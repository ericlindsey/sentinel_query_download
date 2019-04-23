#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use ASF API to search for granules given search parameters found in a config file.
Then generate AWS URL and download.

Created on Fri Oct 13 11:10:47 2017

@author: Eric Lindsey, Earth Observatory of Singapore
"""

import configparser,argparse,requests,csv,subprocess,time,os,errno

# hard-coded URL for ASF query
asf_baseurl='https://api.daac.asf.alaska.edu/services/search/param?'


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
    parser.add_argument('config',type=str,help='supply name of config file to setup processing options. Required.')
    parser.add_argument('--download',action='store_true',help='Download the resulting scenes (default: false)')
    args = parser.parse_args()

    # read config file
    config=configparser.ConfigParser()
    config.optionxform = str #make the config file case-sensitive
    config.read(args.config)
    download_site=config.get('download','download_site')
    aws_base_url=config.get('download','aws_base_url')
    
    # parse the config options directly into a query... this may be too naive
    # get options from config file
    arg_list=config.items('api_search')
    # join as a single argument string
    arg_str='&'.join('%s=%s'%(item[0],item[1]) for item in arg_list)
    # add extra option for csv format.
    arg_str=arg_str+'&output=csv'
    
    # this section should contain 'http-user', 'http-password', plus any other wget options.
    # we join them (also naively) as a single argument string
    asf_wget_options=config.items('asf_download')
    asf_wget_str=' '.join('--%s=%s'%(item[0],item[1]) for item in asf_wget_options)
        
    # form into a query
    argurl=asf_baseurl + arg_str
    # example query:
    # argurl="https://api.daac.asf.alaska.edu/services/search/param?platform=R1\&absoluteOrbit=25234\&output=CSV"

    print('\nRunning ASF API query:')
    print(argurl + '\n')

    # run the ASF query request
    r=requests.post(argurl)
    
    # log the results
    logtime=time.strftime("%Y_%m_%d-%H_%M_%S")
    query_log='asf_query_%s.csv'%logtime
    with open(query_log,'w')as f:
        print('Query result saved to asf_query_%s.csv'%logtime)
        f.write(r.text)
        
    # If a download is requested:
    # parse result into a list of granules, figure out the correct path,
    # and download each one.
    # wget -c option will cause existing files to be automatically skipped
    # (but this causes some overhead; better to tune the query to avoid these files)
    if args.download:
        orig_dir=os.getcwd()
        reader = csv.DictReader(r.text.splitlines())
        for row in reader:
            frame_dir='P' + row['Path Number'].zfill(3) + '/F' + row['Frame Number'].zfill(4)
            print('Downloading granule ', row['Granule Name'], 'to directory', frame_dir)
            
            #log file name
            logfile='log_wget_' + row['Granule Name'] + logtime + '.log'
            
            #run wget command
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
                aws_url = aws_base_url + datefolder + row['Granule Name'] + '/' + row['Granule Name'] + '-pds.browse.png'
                cmd='wget -c --show-progress -o ' + logfile + ' ' + aws_url
                print(cmd)
                status=subprocess.call(cmd, shell=True)
                if status != 0:
                    if download_site == 'AWS':
                        print('Download failed. Perhaps granule is not at AWS? Not retrying.')
                    else:
                        print('Download failed. Trying ASF download instead.')
            if((status != 0 and download_site == 'both') or download_site == 'ASF'):
                asf_url = row['URL']
                cmd='wget -c --show-progress -o ' + logfile + ' ' + asf_wget_str + ' ' + asf_url
                print(cmd)
                #status=subprocess.call(cmd, shell=True)
            os.chdir(orig_dir)
    else:
        print(r.text)

