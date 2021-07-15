#!/bin/bash

# run_cat_s1.sh
# automate-gmtsar function to combine Sentinel-1 frames
# last updated Jan 2021, Eric Lindsey
#
# copy this file to your directory, and edit this code to work for your case.
# this will search for all data in the specified folders, then use the GMTSAR command
# 'create_frame_tops.csh' to combine bursts from all scenes within the given latitude bounds

# defaults
code_path="$GMTSAR_APP/cat_s1.py"
download_path="P*/F*"
orbit_path="."
nproc=1

#manually edit
direction="D" # D or A
pin1="-106.5/35.4" #lon/lat along northern frame edge
pin2="-106.7/34.9" #lon/lat along southern frame edge

# run command
echo "python $code_path $download_path -o $orbit_path -d $direction -l $pin1/$pin2 -n $nproc"
python $code_path $download_path -o $orbit_path -d $direction -l$pin1/$pin2 -n $nproc

