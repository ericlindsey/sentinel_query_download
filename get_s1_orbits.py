#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to link most recent orbit file for each SAFE file.
Created on Thu Jul 15 10:00:01 2021
Last updated April 2023
@author: elindsey
"""
import os,shutil,argparse
import s1_orbit_func

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and download a Sentinel-1 Orbit file (Precise or Restituted) matching an input Granule file (SAFE or zip format). Searches in orbit-dir location, and files will be downloaded there too, then copied or linked to the current directory.')
    parser.add_argument('granules',type=str,nargs='+',action='extend',help='supply name of granule(s) for which to find a matching orbit. Required. Example: S1A_IW_SLC__1SDV_20180810T224749_20180810T224816_023190_02850D_0C43.SAFE')
    parser.add_argument('-o','--orbit-dir',type=str,default='.',help='Directory to download the resulting scenes to (default: current directory)')
    parser.add_argument('-p','--precise',action='store_true',help='Precise orbit file only. (default: precise preferred, but will use restituted if no precise orbit is available.)')
    parser.add_argument('-l','--link',action='store_true',help='Link the files instead of copying them (default: will copy the files to the current location from the --orbit-dir location.)')
    args = parser.parse_args()
    
    print('Checking for matching orbit files.\n')
    for granule in args.granules:
        [sat_ab, sat_mode, date1, date2, orbit_num] = s1_orbit_func.parse_s1_SAFE_name(granule)
        # look for the file, and return filename and whether it is new or existing
        eof_filename,found_existing = s1_orbit_func.get_latest_orbit_file(sat_ab,date1,date2,[args.orbit_dir],download_missing=True,skip_notfound=False,preciseonly=args.precise)
        if eof_filename is not None:
            if found_existing:
                print(f'Found existing file: {eof_filename}')
            else:
                print(f'Downloaded new file: {eof_filename}')
    print('\nDone getting orbits.\n')

