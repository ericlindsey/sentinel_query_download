#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 11:45:24 2017

@author: elindsey
"""

import os,sys,shutil,glob,datetime,multiprocessing,random,string
import requests,json,cgi,tarfile
from xml.etree import ElementTree
import s1_orbit_func

######################## Sentinel-specific functions ########################
# This satellite is a real nightmare for my attempts at standardization 


def unzip_images_to_dir(filelist,unzip_dir):
    """
    For a list of zipped S1 SLC files, unzip them to a temporary directory (not parallel).
    """
    cmds=[]
    owd=os.getcwd()
    # go to the output directory so the unzipped results will fall there:
    os.chdir(unzip_dir)
    for image in filelist:
        item=os.path.abspath(image)
        filename=os.path.basename(item)
        cmd = 'unzip %s'%item
        run_command(cmd,logFile='log_%s.txt'%filename)
    os.chdir(owd)


def find_images_by_orbit(dirlist,s1_orbit_dirs,ftype='SAFE'):
    """
    For each Sentinel-1 satellite, find all images that were acquired on the same orbit, and order them by time
    """
    valid_modes = ['IW_SLC'] #we match only IW_SLC data
    
    #dictionaries will keep track of the results
    names       = dict()
    start_times = dict()
    eofs        = dict()
    
    for searchdir in dirlist:
        list_of_images=glob.glob('%s/S1*%s'%(searchdir,ftype))
        #print('in',searchdir)
        #print('found list',list_of_images,'\n')
        
        for item in list_of_images:
            # we want the full path and also just the file name
            item=os.path.abspath(item)
            file=os.path.basename(item)
            
            # get A/B, sat. mode, dates, orbit ID from the file name
            [sat_ab,sat_mode,image_start,image_end,orbit_num] = s1_orbit_func.parse_s1_SAFE_name(file)
            #print('Read file:',file,'parameters:',sat_ab,sat_mode,image_start,image_end,orbit_num)

            if sat_mode in valid_modes:
                #Find matching EOF
                eof_name = s1_orbit_func.get_latest_orbit_file(sat_ab,image_start,image_end,s1_orbit_dirs,skip_notfound=True)
                if eof_name is not None:
                    #print('Got EOF:',eof_name)
                
                    #add A or B to the orbit number and use as the unique ID for identifying orbits
                    ab_orbit='S1%s_%06d'%(sat_ab,orbit_num)
                    if ab_orbit not in names:
                        names[ab_orbit] = []
                        start_times[ab_orbit] = []
                        eofs[ab_orbit] = eof_name
                    elif eof_name != eofs[ab_orbit]:
                        #we've already found one scene from this orbit. check that it matches the same orbit file 
                        print('Error: found two scenes from same orbit number matching different EOFs. Check your data.')
                        sys.exit(1)
                    
                    #keep the images in time order. Find the index of the first time that is later than the image's time
                    timeindx=0
                    for starttime in start_times[ab_orbit]:
                        if starttime < image_start:
                            timeindx+=1
                    names[ab_orbit].insert(timeindx,item)
                    start_times[ab_orbit].insert(timeindx,image_start)
    return names, eofs


def write_ll_pins(fname, lons, lats, asc_desc):
    """
    Put lat/lon pairs in time order and write to a file.
    Lower latitude value comes first for 'A', while for 'D' higher lat. is first
    """
    if (asc_desc == 'D' and lats[0] < lats[1]) or (asc_desc == 'A' and lats[0] > lats[1]):
        lats.reverse()
        lons.reverse()
    lonlats=['%f %f'%(i,j) for i,j in zip(lons,lats)]
    write_list(fname,lonlats)


def create_frame_tops_parallel(filelist,eof,llpins,logfile,workdir,unzipped):
    """
    Run the GMTSAR command create_frame_tops.csh to combine bursts within the given latitude bounds
    Modified version enables running in parallel by running in a temporary subdirectory.
    """
    # to run in parallel, we have to do everything inside a unique directory
    # this is because GMTSAR uses constant temp filenames that will collide with each other
    # in this case, the colliding name is the temp folder 'new.SAFE'
    os.makedirs(workdir, exist_ok=False)
    cwd=os.getcwd()
    os.chdir(workdir)

    # If files are not already unzipped, unzip them in a subdirectory first
    if not unzipped:
        temp_unzip_dir = 'temp_unzip'
        os.makedirs(temp_unzip_dir, exist_ok=False)
        unzip_images_to_dir(filelist,temp_unzip_dir)
        # need to provide full path to glob to get full paths back
        #safelist = glob.glob('%s/%s/%s/S1*SAFE'%(cwd,workdir,temp_unzip_dir))
        safelist = sorted(glob.glob('%s/%s/%s/S1*SAFE'%(cwd,workdir,temp_unzip_dir)), key=os.path.basename)
    else:
        #safelist = filelist
        safelist = sorted(filelist,key=os.path.basename)

    # write file list to the current directory
    write_list('SAFE.list', safelist)

    # copy orbit file to the current directory, required for create_frame_tops.csh
    shutil.copy2(eof,os.getcwd())
    local_eof=os.path.basename(eof)

    # copy llpins file to current directory
    shutil.copy2(os.path.join(cwd,llpins),llpins)

    # create GMTSAR command and run it
    #cmd = '/home/share/insarscripts/automate/gmtsar_functions/create_frame_tops.csh SAFE.list %s %s 1 %s'%(local_eof, llpins, logfile)
    cmd = 'create_frame_tops.csh SAFE.list %s %s 1'%(local_eof, llpins)
    run_command(cmd,logFile=logfile)

    # copy result back to main directory
    result_safe=glob.glob('S1*SAFE')[0]
    shutil.move(result_safe,os.path.join(cwd,result_safe))
    shutil.move(logfile,os.path.join(cwd,logfile))

    # clean up
    os.chdir(cwd)
    shutil.rmtree(workdir)


def run_command(command, logFile=''):
    """
    Use subprocess.call to run a command.
    If optional argument logFile is passed, redirect stdout and stderr to that file.
    """
    print('running', command)
    if not logFile.strip():
        #no logging, just run command as-is
        status=subprocess.call(command, shell=True)
    else:
        with open(logFile,'w') as outFile:
            status=subprocess.call(command, shell=True, stdout=outFile, stderr=outFile)
    if status != 0:
        print('Python encountered an error in the command:')
        print(command)
        print('error code:', status)
        sys.exit(1)


def run_logged_command(command):
    """
    Used for pool.map where only one argument can be passed - before running, strip off last argument and use as logfile.
    """
    #remove last argument and use it as log file
    logfile=command.split()[-1]
    cmd=' '.join(command.split()[0:-1])
    #now run the command with logging
    run_command(cmd,logFile=logfile)


def write_list(fname,strlist):
    """
    write a list of strings to a file
    """
    with open(fname,'w') as f:
        f.write('\n'.join(strlist))
        f.write('\n')
