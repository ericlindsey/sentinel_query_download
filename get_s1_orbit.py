#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to download most recent orbit file, given a downloaded .SAFE or .SAFE.zip file name
Created on Thu Jul 15 10:00:01 2021
@author: elindsey
"""
import requests,cgi,json,os,sys,argparse
from xml.etree import ElementTree
import s1_orbit_func

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and download a Sentinel-1 Orbit file (Precise or Restituted) matching an input Granule file (SAFE or zip format)')
    parser.add_argument('granule',type=str,help='supply name of granule for which to find a matching orbit. Required. Example: S1A_IW_SLC__1SDV_20180810T224749_20180810T224816_023190_02850D_0C43.SAFE')
    parser.add_argument('-d','--dir',type=str,default='.',help='Directory to download the resulting scenes to (default: current directory)')
    parser.add_argument('-p','--precise',action='store_true',help='Precise orbit file only. (default: either precise or restituted, whichever is most recent)')
    args = parser.parse_args()

    # run the download and return filename
    eof_filename = s1_orbit_func.download_latest_orbit(args.granule,args.dir,args.precise)
    print(f'Downloaded file: {eof_filename}')

