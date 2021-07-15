#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use ASF API to search for granules given search parameters found in a config file.
Then generate URL and download from either AWS open dataset or ASF.

First version: October 2017
Modified April 2019 to include AWS downloading
Modified June 2019 to enable parallel downloads
Modified Oct 2019 to enable multiple file types (e.g. csv,json,kml)
Modified July 2021, minor fixes

@author: Eric Lindsey, University of New Mexico
"""

import configparser,argparse,requests,csv,subprocess,time,os
#optional use urllib instead of wget
#from urllib.request import urlopen
import multiprocessing as mp

# hard-coded ASF query URL:
asf_baseurl='https://api.daac.asf.alaska.edu/services/search/param?'

# hard-coded AWS base URL for public dataset downloads:
aws_baseurl = 'http://sentinel1-slc-seasia-pds.s3-website-ap-southeast-1.amazonaws.com/datasets/slc/v1.1/'

def downloadGranule(row):
    orig_dir=os.getcwd()
    download_site = row['Download Site']
    frame_dir='P' + row['Path Number'].zfill(3) + '/F' + row['Frame Number'].zfill(4)
    print('Downloading granule ', row['Granule Name'], 'to directory', frame_dir)
    #create frame directory
    os.makedirs(frame_dir, exist_ok=True)
    os.chdir(frame_dir)
    status=0
    if(download_site == 'AWS' or download_site == 'both'):
        print('Try AWS download first.')
        # create url for AWS download, based on the granule name
        row_date=row['Acquisition Date']
        row_year=row_date[0:4]
        row_month=row_date[5:7]
        row_day=row_date[8:10]
        datefolder= row_year + '/' + row_month + '/' + row_day +'/'
        aws_url = aws_baseurl + datefolder + row['Granule Name'] + '/' + row['Granule Name'] + '.zip'
        # run the download command
        status = downloadGranule_wget(aws_url)
        if status != 0:
            if download_site == 'AWS':
                print('AWS download failed. Granule not downloaded.')
            else:
                print('AWS download failed. Trying ASF download instead.')
    if((status != 0 and download_site == 'both') or download_site == 'ASF'):
        asf_url = row['asf_wget_str'] + ' ' + row['URL']
        # run the download command
        status = downloadGranule_wget(asf_url)
        if status != 0:
            print('ASF download failed. Granule not downloaded.')
    os.chdir(orig_dir)

## urllib not currently used. Test for speed?
#def downloadGranule_urllib(url):
#    fzip = url.split('/')[-1]
#    if os.path.isfile(fzip) == False:
#        print("Using python urllib to download "+url+" to file "+fzip)
#        with urlopen(url) as response, open(fzip, 'wb') as ofile:
#            shutil.copyfileobj(response, ofile)
#    return 0

def downloadGranule_wget(options_and_url):
    cmd='wget -c --no-check-certificate -q ' + options_and_url
    print(cmd)
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.returncode

if __name__ == '__main__':
    # read command line arguments and parse config file.
    parser = argparse.ArgumentParser(description='Use http requests and wget to search and download data from the ASF archive, based on parameters in a config file.')
    parser.add_argument('config',type=str,help='supply name of config file to set up API query. Required.')
    parser.add_argument('--download',action='store_true',help='Download the resulting scenes (default: false)')
    parser.add_argument('--verbose',action='store_true',help='Print the query result to the screen (default: false)')
    #parser.add_argument('--save-csv',action='store_true',help='Save the resulting csv file (default: false)')
    args = parser.parse_args()

    # read config file
    config=configparser.ConfigParser()
    config.optionxform = str #make the config file case-sensitive
    config.read(args.config)
    download_site=config.get('download','download_site',fallback='both')
    nproc=config.getint('download','nproc',fallback=1)
    output_format=config.get('api_search','output',fallback='csv')
    
    # we parse the config options directly into a query... this may be too naive
    arg_list=config.items('api_search')
    # join as a single argument string
    arg_str='&'.join('%s=%s'%(item[0],item[1]) for item in arg_list)
    
    # form into a query
    argurl=asf_baseurl + arg_str
    # example query:
    # argurl="https://api.daac.asf.alaska.edu/services/search/param?platform=R1\&absoluteOrbit=25234\&output=CSV"

    # run the ASF query request
    print('\nRunning ASF API query:')
    print(argurl + '\n')
    r=requests.post(argurl)
    # parse rows if csv, else we just operate on the 'r' object
    if output_format == 'csv':
        reader = csv.DictReader(r.text.splitlines())
        rows=list(reader)
    
    # save the results to a file
    logtime=time.strftime("%Y_%m_%d-%H_%M_%S")
    query_log='asf_query_%s.%s'%(logtime,output_format)
    with open(query_log,'w')as f:
        print('Query result saved to asf_query_%s.%s'%(logtime,output_format))
        f.write(r.text)

    # print the results to the screen
    if args.verbose:
        if output_format == 'csv':
            # print the results in a nice format
            numscenes=len(rows)
            plural_s = 's' if numscenes > 1 else ''
            if numscenes > 0:
                print("Found %s scene%s." %(numscenes,plural_s))
                for row in rows:
                    print('Scene %s, Path %s / Frame %s' %(row['Granule Name'], row['Path Number'], row['Frame Number']))
        else:
            print(r.text)
        
    # If a download is requested:
    # parse result into a list of granules, figure out the correct path, and download each one.
    if output_format != 'csv' and args.download:
        print('Error: cannot download unless output format is set to csv. Doing nothing.')
    if output_format == 'csv' and args.download:
        if nproc > 1:
            print('\nRunning %d downloads in parallel.'%nproc)
        else:
            print('\nDownloading 1 at a time.')
        # need to pass http-user and http-password for ASF downloads.
        # this section should contain 'http-user', 'http-password', plus any other wget options.
        # we join them (naively) as a single argument string
        if download_site != 'AWS':
            # first, check for missing values:
            if not (config.has_section('asf_download') and config.has_option('asf_download','http-user') \
                and config.has_option('asf_download','http-password') and len(config.get('asf_download','http-user'))>0 \
                and len(config.get('asf_download','http-password')) > 0):
                raise ValueError('ASF username or password missing in config file.')
            asf_wget_options=config.items('asf_download')
            asf_wget_str=' '.join('--%s=%s'%(item[0],item[1]) for item in asf_wget_options)
        else:
            asf_wget_str=''
        downloadList = []
        for row in rows:
            downloadDict = row
            # add some extra info to the csv row for download purposes
            downloadDict['Download Site'] = download_site
            downloadDict['asf_wget_str'] = asf_wget_str
            downloadList.append(downloadDict)
        # map list to multiprocessing pool
        pool = mp.Pool(processes=nproc)
        pool.map_async(downloadGranule, downloadList, chunksize=1)
        pool.close()
        pool.join()
        print('\nDownload complete.\n')
    else:
        print('\nNot downloading.\n')

    print('Sentinel query complete.\n')

