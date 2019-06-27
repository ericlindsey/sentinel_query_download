#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use ASF API to search for granules given search parameters found in a config file.
Then generate URL and download from either AWS open dataset or ASF.

First version: October 2017
Modified April 2019 to include AWS downloading
Modified June 2019 to enable parallel downloads

@author: Eric Lindsey, Earth Observatory of Singapore
"""

import configparser,argparse,requests,csv,subprocess,time,os,errno,glob,shutil
#optional use urllib instead of wget
#from urllib.request import urlopen
import multiprocessing as mp

# hard-coded URL for ASF query
asf_baseurl='https://api.daac.asf.alaska.edu/services/search/param?'

# AWS base: included as parameter in config file
#aws_base_url = 'http://sentinel1-slc-seasia-pds.s3-website-ap-southeast-1.amazonaws.com/datasets/slc/v1.1/'

def downloadGranule(row):
    orig_dir=os.getcwd()
    frame_dir='P' + row['Path Number'].zfill(3) + '/F' + row['Frame Number'].zfill(4)
    print('Downloading granule ', row['Granule Name'], 'to directory', frame_dir)
    #create frame directory
    mkdir_p(frame_dir)
    os.chdir(frame_dir)
    status=0
    if(download_site == 'AWS' or download_site == 'both'):
        # create url for AWS download, based on the granule name
        row_date=row['Acquisition Date']
        row_year=row_date[0:4]
        row_month=row_date[5:7]
        row_day=row_date[8:10]
        datefolder= row_year + '/' + row_month + '/' + row_day +'/'
        aws_url = aws_base_url + datefolder + row['Granule Name'] + '/' + row['Granule Name'] + '.zip'
        # run the download command
        status = downloadGranule_wget(aws_url)
        if status != 0:
            if download_site == 'AWS':
                print('Amazon download failed. Perhaps granule is not at AWS? Not retrying, as only AWS is specified.')
            else:
                print('Amazon download failed. Trying ASF download instead.')
    if((status != 0 and download_site == 'both') or download_site == 'ASF'):
        asf_url = asf_wget_str + ' ' + row['URL']
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
    status=subprocess.call(cmd, shell=True)
    return status

# implement shell 'mkdir -p' to create directory trees with one command, and ignore 'directory exists' error
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

if __name__ == '__main__':
 
    # read command line arguments and parse config file.
    parser = argparse.ArgumentParser(description='Use http requests and wget to search and download data from the ASF archive, based on parameters in a config file.')
    parser.add_argument('config',type=str,help='supply name of config file to set up API query. Required.')
    parser.add_argument('--download',action='store_true',help='Download the resulting scenes (default: false)')
    parser.add_argument('--save-csv',action='store_true',help='Save the resulting csv file (default: false)')
    args = parser.parse_args()

    # read config file
    config=configparser.ConfigParser()
    config.optionxform = str #make the config file case-sensitive
    config.read(args.config)
    download_site=config.get('download','download_site')
    aws_base_url=config.get('download','aws_base_url')
    nproc=config.getint('download','nproc',fallback=1)
    
    # we parse the config options directly into a query... this may be too naive
    arg_list=config.items('api_search')
    # join as a single argument string
    arg_str='&'.join('%s=%s'%(item[0],item[1]) for item in arg_list)
    # add extra option for csv format.
    arg_str=arg_str+'&output=csv'
    
    # form into a query
    argurl=asf_baseurl + arg_str
    # example query:
    # argurl="https://api.daac.asf.alaska.edu/services/search/param?platform=R1\&absoluteOrbit=25234\&output=CSV"

    # run the ASF query request
    print('\nRunning ASF API query:')
    print(argurl + '\n')
    r=requests.post(argurl)

    # print the results in a nice format
    reader = csv.DictReader(r.text.splitlines())
    rows=list(reader)
    numscenes=len(rows)
    if numscenes > 1:
        plural_s='s'
    else:
        plural_s = ''
    if numscenes > 0:
        print("Found %s scene%s." %(numscenes,plural_s))
        for row in rows:
            print('Scene %s, Path %s / Frame %s' %(row['Granule Name'], row['Path Number'], row['Frame Number']))
    
    # save the results to a csv file
    if args.save_csv:
        logtime=time.strftime("%Y_%m_%d-%H_%M_%S")
        query_log='asf_query_%s.csv'%logtime
        with open(query_log,'w')as f:
            print('\nQuery result saved to asf_query_%s.csv'%logtime)
            f.write(r.text)
        
    # If a download is requested:
    # parse result into a list of granules, figure out the correct path, and download each one.
    if args.download:
        if nproc > 1:
            print('\nRunning %d downloads in parallel.'%nproc)
        else:
            print('\nDownloading scene%s 1 at a time.'%plural_s)
        downloadList = []
        for row in rows:
            downloadDict = row
            # add some extra info to the csv row for download purposes
            downloadDict['Download Site'] = download_site
            if download_site != 'AWS':
                # need to pass http-user and http-password for ASF downloads
                # this section should contain 'http-user', 'http-password', plus any other wget options.
                # we join them (also naively) as a single argument string
                asf_wget_options=config.items('asf_download')
                asf_wget_str=' '.join('--%s=%s'%(item[0],item[1]) for item in asf_wget_options)
                downloadDict['asf_wget_str'] = asf_wget_str
            downloadList.append(downloadDict)
        # map list to multiprocessing pool
        pool = mp.Pool(processes=nproc)
        pool.map_async(downloadGranule, downloadList, chunksize=1)
        pool.close()
        pool.join()
        print('\nDownload%s complete.\n'%plural_s)
    else:
        print('\nNot downloading scene%s.\n'%plural_s)

print('Sentinel query complete.\n')

