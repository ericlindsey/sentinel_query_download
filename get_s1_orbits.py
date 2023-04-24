#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to link most recent orbit file for each SAFE file.
Created on Thu Jul 15 10:00:01 2021
Last updated April 2023
@author: elindsey
"""
import os,shutil,argparse,multiprocessing
import s1_orbit_func

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and download a Sentinel-1 Orbit file (Precise or Restituted) matching an input Granule file (SAFE or zip format). Searches in orbit-dir location, and files will be downloaded there too, then copied or linked to the current directory.')
    parser.add_argument('granules',type=str,nargs='+',action='extend',help='supply name of granule(s) for which to find a matching orbit. Required. Example: S1A_IW_SLC__1SDV_20180810T224749_20180810T224816_023190_02850D_0C43.SAFE')
    parser.add_argument('-o','--orbit-dir',type=str,default='.',help='Directory to download the resulting scenes to (default: current directory)')
    parser.add_argument('-p','--precise',action='store_true',help='Precise orbit file only. (default: precise preferred, but will use restituted if no precise orbit is available.)')
    parser.add_argument('-l','--link',action='store_true',help='Link the files instead of copying them (default: will copy the files to the current location from the --orbit-dir location.)')
    parser.add_argument('-n','--nproc',type=int,default=16,help='Number of processors to run in parallel, optional (default: 16)')
    args = parser.parse_args()
    
    #set defaults
    download_missing = True
    skip_notfound = False
    print_results = True

    # create orbit dictionary
    orbitlist = {}
    print('Checking for matching orbit files.\n')
    for granule in args.granules:
        [sat_ab, sat_mode, start, end, orbit_num] = s1_orbit_func.parse_s1_SAFE_name(granule)
        if orbit_num in orbitlist:
        # if the item exists in the dictionary, extend the start/end time as necessary
            if start < orbitlist[orbit_num]['start']:
                orbitlist[orbit_num]['start'] = start
            if end > orbitlist[orbit_num]['end']:
                orbitlist[orbit_num]['end'] = end
        else:
            # if orbit num is not in the orbit dict, add to it
            orbitlist[orbit_num] = {'sat_ab': sat_ab, 'start': start, 'end': end}

    # compose the list of argument tuples to pass to the function
    argslist=[]
    for orbit,vals in orbitlist.items():
        sat_ab = vals['sat_ab']
        start = vals['start']
        end = vals['end']
        argslist.append((sat_ab,start,end,[args.orbit_dir],download_missing,skip_notfound,args.precise,print_results))

    # for each identified orbit, look for the file, and download if necessary
    multiprocessing.set_start_method("spawn")
    with multiprocessing.get_context("spawn").Pool(processes=args.nproc) as pool:
        results = pool.starmap(s1_orbit_func.get_latest_orbit_file, argslist, chunksize=1)

    print('\nDone getting orbits.\n')

