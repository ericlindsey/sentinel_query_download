#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to link most recent orbit file for each SAFE file.
Created on Thu Jul 15 10:00:01 2021
@author: elindsey
"""
import os,shutil,argparse
import s1_orbit_func

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and download a Sentinel-1 Orbit file (Precise or Restituted) matching an input Granule file (SAFE or zip format). Searches in orbit-dir location, and files will be downloaded there too, then copied or linked to the current directory.')
    parser.add_argument('granules',type=str,nargs='+',action='extend',help='supply name of granule(s) for which to find a matching orbit. Required. Example: S1A_IW_SLC__1SDV_20180810T224749_20180810T224816_023190_02850D_0C43.SAFE')
    parser.add_argument('-o','--orbit-dir',type=str,default='/home/bigdata/orbits/S1',help='Directory to download the resulting scenes to (default: current directory)')
    parser.add_argument('-p','--precise',action='store_true',help='Precise orbit file only. (default: either precise or restituted, whichever is most recent)')
    parser.add_argument('-l','--link',action='store_true',help='Link the files instead of copying them (default: will copy the files to the current location from the --orbit-dir location.)')
    args = parser.parse_args()

    for granule in args.granules:
        [sat_ab, sat_mode, date1, date2, orbit_num] = s1_orbit_func.parse_s1_SAFE_name(granule)
        # look for the file or download it, and return filename
        eof_filename = s1_orbit_func.get_latest_orbit_file(sat_ab,date1,date2,[args.orbit_dir],download_missing=True,skip_notfound=False,preciseonly=args.precise)
        print(f'Got file: {eof_filename}')
        dest_file=os.path.join(os.getcwd(),os.path.basename(eof_filename))
        print(dest_file)
        if args.link:
            os.symlink(eof_filename,dest_file)
        else:
            shutil.copy(eof_filename,dest_file)

