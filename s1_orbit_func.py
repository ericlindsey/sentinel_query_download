#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 11:45:24 2017

@author: elindsey
"""

import os,sys,shutil,glob,datetime,multiprocessing,random,string
import requests,json,cgi,tarfile
from xml.etree import ElementTree


def parse_s1_SAFE_name(safe_name):
    """
    SAFE file has name like S1A_IW_SLC__1SDV_20150224T114043_20150224T114111_004764_005E86_AD02.SAFE (or .zip)
    Function returns a list of 2 strings, 2 datetime objects and one integer ['A', 'IW_SLC', '20150224T114043','20150224T114111', 004764]
    """
    #make sure we have just the file name
    safe_name = os.path.basename(safe_name)
    #extract string components and convert to datetime objects
    sat_ab   = safe_name[2]
    sat_mode = safe_name[4:10]
    date1    = datetime.datetime.strptime(safe_name[17:32],'%Y%m%dT%H%M%S')
    date2    = datetime.datetime.strptime(safe_name[33:48],'%Y%m%dT%H%M%S')
    orbit_num= int(safe_name[49:55])
    return [sat_ab, sat_mode, date1, date2, orbit_num]



def get_latest_orbit_file(sat_ab,imagestart,imageend,s1_orbit_dirs,download_missing=True,skip_notfound=True,preciseonly=False):
    """
    Orbit files have 3 dates: production date, start and end range. Image files have 2 dates: start, end.
    We want to find the latest file (most recent production) whose range includes the range of the image.
    If none is found, look for the file from ESA by default.
    Return string includes absolute path to file.
    """
    eoflist=[]
    eofprodlist=[]
    latest_eof=None
    # add a half hour to the image start/end times to ensure we have enough coverage in the orbit file
    imagestart_pad = imagestart - datetime.timedelta(hours=0.5)
    imageend_pad = imageend + datetime.timedelta(hours=0.5)
    
    # first, we check if this file has already been downloaded - look in the provided folders
    # loop over multiple orbit folders, if provided
    for s1_orbit_dir in s1_orbit_dirs:
        # loop over orbit files in this folder
        for item in glob.glob(s1_orbit_dir+"/S1"+sat_ab+"*.EOF"):
            #get basename, and read dates from string
            eof=os.path.basename(item)
            [eofprod,eofstart,eofend] = get_dates_from_eof(eof)
            #check if the EOF validity dates span the entire image
            if eofstart < imagestart_pad and eofend > imageend_pad:
                # exclude case where preciseonly is set and image is RESORB type
                if not (preciseonly and 'AUX_RESORB' in eof):
                    eoflist.append(os.path.abspath(os.path.join(s1_orbit_dir,eof)))
                    #record the production time to ensure we get the most recent one
                    eofprodlist.append(eofprod)       

    #print the most recent valid EOF found in the folders
    if eoflist:
        latest_eof = eoflist[eofprodlist.index(max(eofprodlist))]
    # if no file was found locally, download from ESA if this is requested
    elif download_missing:
        print('No matching orbit file found locally, downloading from ESA')
        tstart=imagestart_pad.strftime('%Y-%m-%dT%H:%M:%S')
        tend=imageend_pad.strftime('%Y-%m-%dT%H:%M:%S')
        orbit = get_latest_orbit_copernicus_api(sat_ab,tstart,tend,'AUX_POEORB')
        if not orbit and not preciseonly:
            orbit = get_latest_orbit_copernicus_api(sat_ab,tstart,tend,'AUX_RESORB')        
        if orbit:
            # set download location to one of the user-supplied folders. We assume the user would either supply one folder, or two folders with 'resorb' coming second.
            if len(s1_orbit_dirs)>1 and orbit['orbit_type'] == 'AUX_RESORB':
                target_dir=s1_orbit_dirs[1]
            else:
                target_dir=s1_orbit_dirs[0]
            # download and return the full path to the file
            print(target_dir)
            latest_eof = download_copernicus_orbit_file(target_dir,orbit['remote_url'])

    # nothing was found - print a warning or error
    if not latest_eof or not os.path.exists(latest_eof):
        if skip_notfound:
            print("Warning: No matching orbit file found for Sentinel-1%s during time %s to %s in %s - skipping"%(sat_ab,imagestart_pad,imageend_pad,s1_orbit_dirs))
            return None
        else:
            print("Error: No matching orbit file found for Sentinel-1%s during time %s to %s in %s"%(sat_ab,imagestart_pad,imageend_pad,s1_orbit_dirs))
            sys.exit(1)

    return latest_eof


def download_latest_orbit(granule,target_dir,preciseonly):

    # parse the SAFE filename to get sat_ab and start/end dates
    [sat_ab, sat_mode, date1, date2, orbit_num] = parse_s1_SAFE_name(granule)
    
    #pad times by 30 min
    imagestart_pad = date1 - datetime.timedelta(hours=0.5)
    imageend_pad   = date2 + datetime.timedelta(hours=0.5)

    # put padded times in API format
    tstart=imagestart_pad.strftime('%Y-%m-%dT%H:%M:%S')
    tend=imageend_pad.strftime('%Y-%m-%dT%H:%M:%S')
    
    # try to download the precise orbit first
    orbit = get_latest_orbit_copernicus_api(sat_ab,tstart,tend,'AUX_POEORB')

    # try the restituted orbit if the precise failed
    if not orbit:
        if preciseonly:
            print("Error: option --precise was set, but no precise orbit file found. Not trying restituted orbit search")
            sys.exit(1)
        else:
            orbit = get_latest_orbit_copernicus_api(sat_ab,tstart,tend,'AUX_RESORB')        

    # download the orbit file
    eof_filename = download_copernicus_orbit_file(target_dir, orbit['remote_url'])
    return eof_filename


def get_latest_orbit_copernicus_api(sat_ab,start_time,end_time,orbit_type):
    """
    Use the Copernicus GNSS products API to find the latest orbit file.
    Input example formats: 'A', '2018-08-10T22:47:19', '2018-08-10T22:48:16', 'AUX_POEORB'
    Returns a python dictionary, with elements 'orbit_type' (matching the input orbit_type) and 'remote_url'.
    """
    # modified by E. Lindsey, April 2021
    
    # some hard-coded URLs to make the API work
    scihub_url='https://scihub.copernicus.eu/gnss/odata/v1/Products'
    # these are from the namespaces of the XML file returned in the query. Hopefully not subject to change?
    w3_url='{http://www.w3.org/2005/Atom}'
    m_url='{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
    d_url='{http://schemas.microsoft.com/ado/2007/08/dataservices}'

    # compose search filter
    filterstring = f"startswith(Name,'S1{sat_ab}') and substringof('{orbit_type}',Name) and ContentDate/Start lt datetime'{start_time}' and ContentDate/End gt datetime'{end_time}'"
    
    # create HTTPS request and get response
    params = { '$top': 1, '$orderby': 'ContentDate/Start asc', '$filter': filterstring }
    search_response = requests.get(url='https://scihub.copernicus.eu/gnss/odata/v1/Products', params=params, auth=('gnssguest','gnssguest'))
    search_response.raise_for_status()

    # parse XML tree from response
    tree = ElementTree.fromstring(search_response.content)
    
    #extract w3.org URL that gets inserted into all sub-element names for some reason
    w3url=tree.tag.split('feed')[0]
    
    # extract the product's hash-value ID
    product_ID=tree.findtext(f'.//{w3_url}entry/{m_url}properties/{d_url}Id')
    product_url = f"{scihub_url}('{product_ID}')/$value"
    product_name=tree.findtext(f'./{w3url}entry/{w3url}title')

    # return the orbit name, type, and download URL
    if product_ID is not None:
        orbit={'name':product_name, 'orbit_type':orbit_type, 'remote_url':product_url}
    else:
        orbit=None
    return orbit

def download_copernicus_orbit_file(dest_folder,remote_url):
    """
    Download orbit file returned by the Copernicus GNSS products API.
    Inputs: destination folder (absolute or relative path) and the remote URL, with a format like: https://scihub.copernicus.eu/gnss/odata/v1/Products('3a773f7a-0602-44e4-b4c0-609b7f4291f0')/$value
    Returns the absolute path of the saved file.
    """
    # created by E. Lindsey, April 2021

    # check that the output folder exists
    os.makedirs(dest_folder, exist_ok = True)

    # download the orbit file
    dl_response = requests.get(url=remote_url, auth=('gnssguest','gnssguest'))

    # find the filename in the header
    header = dl_response.headers['content-disposition']
    header_value, header_params = cgi.parse_header(header)

    #compose the full filename
    eof_filename = os.path.abspath(os.path.join(dest_folder,header_params['filename']))

    # save the file with the correct filename
    open(eof_filename, 'wb').write(dl_response.content)

    return eof_filename


def get_dates_from_eof(eof_name):
    """
    EOF file has name like S1A_OPER_AUX_POEORB_OPOD_20170917T121538_V20170827T225942_20170829T005942.EOF
    Function returns a list of 3 datetime objects matching the strings ['20170917T121538','20170827T225942','20170829T005942']
    """
    #make sure we have just the file basename
    eof_name = os.path.basename(eof_name)
    #parse string by fixed format
    date1=datetime.datetime.strptime(eof_name[25:40],'%Y%m%dT%H%M%S')
    date2=datetime.datetime.strptime(eof_name[42:57],'%Y%m%dT%H%M%S')
    date3=datetime.datetime.strptime(eof_name[58:73],'%Y%m%dT%H%M%S')
    return [date1,date2,date3]

