Sentinel-1 query and download script
------
Eric Lindsey, University of New Mexico

Last updated: July 2021

This repository contains two scripts:

(1) a simple script that enables easy search and download of Sentinel-1 (or other SAR) data hosted at the Alaska Satellite Facility (ASF) using the ASF API. For help on this API, visit https://asf.alaska.edu/api/.

(2) a script that calls GMTSAR functions to combine the bursts from separate geotiff images in neighboring frames into your own custom frame.

sentinel_query_download.py
------
The basic use of the first script is as follows: enter API keywords and values in a config file (example included), then pass this file as a single argument on the command line. The script will generate an API query, and download the resulting .csv file of results.

The default is to return a search query (csv file) but not download the data. To download the granules after searching, add the command-line option --download. To print out a human-readable table of the results to the screen, use --verbose.

Here is a simple config file example, which returns IW scenes collected during part of April and May 2019 from Path 56 over Albuquerque, NM:

    [api_search]
    output = csv
    platform = Sentinel-1A,Sentinel-1B
    processingLevel = SLC
    beamMode = IW
    intersectsWith = POLYGON((-106.7975 34.9141,-106.3267 34.9141,-106.3267 35.3502,-106.7975 35.3502,-106.7975 34.9141))
    start=2019-04-05T00:00:00UTC
    end=2019-05-05T00:00:00UTC
    relativeOrbit=56

    [download]
    download_site = both
    nproc = 2

    [asf_download]
    http-user = <username>
    http-password = <password>

To run the code with the above config file:

    python sentinel_query_download.py sentinel_query.config --verbose

This should result in the following output:

    Running ASF API query:
    https://api.daac.asf.alaska.edu/services/search/param?output=csv&platform=Sentinel-1A,Sentinel-1B&processingLevel=SLC&beamMode=IW&intersectsWith=POLYGON((-106.7975 34.9141,-106.3267 34.9141,-106.3267 35.3502,-106.7975 35.3502,-106.7975 34.9141))&start=2019-04-01T00:00:00UTC&end=2019-05-05T00:00:00UTC&relativeOrbit=56
    
    Query result saved to asf_query_2021_01_20-11_45_17.csv
    Found 6 scenes.
    Scene S1A_IW_SLC__1SDV_20190504T131059_20190504T131126_027078_030D08_D71A, Path 56 / Frame 477
    Scene S1A_IW_SLC__1SDV_20190504T131035_20190504T131102_027078_030D08_D9ED, Path 56 / Frame 472
    Scene S1A_IW_SLC__1SDV_20190422T131059_20190422T131126_026903_0306A6_A4FD, Path 56 / Frame 477
    Scene S1A_IW_SLC__1SDV_20190422T131034_20190422T131101_026903_0306A6_B8F4, Path 56 / Frame 472
    Scene S1A_IW_SLC__1SDV_20190410T131058_20190410T131125_026728_03005A_EE7F, Path 56 / Frame 477
    Scene S1A_IW_SLC__1SDV_20190410T131034_20190410T131100_026728_03005A_33F2, Path 56 / Frame 472
    
    Not downloading.
    
    Sentinel query complete.

If you are satisfied with the scenes found, then run the code again with the --download option:

    python sentinel_query_download.py sentinel_query.config --verbose --download

If you set download_site = both, the script is set up to prefer downloading from the AWS Sentinel-1 Public Dataset for Southeast Asia; if no file is found there we fall back to downloading from ASF directly (this requires an ASF account). To force ASF-only downloading, set download_site = ASF. For more information on the AWS dataset, see https://registry.opendata.aws/sentinel1-slc-seasia-pds/ - this includes all SLC data acquired over Southeast Asia and parts of East Asia by Sentinel-1, and is hosted in the Singapore AWS region. Depending on your location, this may be much faster (or slower) than downloading from ASF directly.

Running multiple downloads in parallel is possible through the python multiprocessing toolbox, via the config file option 'nproc'. The true effective speedup from running many downloads at the same time has not been tested; this may depend on your own storage and bandwidth situation.

cat_s1.py
------

To use the second script, you are encouraged to make use of the driver script 'run_cat_s1.sh'. This contains all the parameters and options you need to set. In short:

1. Setup defaults. Set the code path, and location where you downloaded the files. If you want the orbit files to be stored somewhere other than the current directory, change this value too. Finally, you can run with multiple processors - note this script does a LOT of disk I/O, so multiple processors will only speed things up if you are doing this all on a solid-state-drive. Otherwise, using more than one processor will likely slow things down!

```
code_path="$GMTSAR_APP/cat_s1.py"
download_path="../download/P*/F*"
orbit_path="."
nproc=1
```    
    
2. Set parameters for your data. You need to specify whether the track is Descending or Ascending with a D or A, and then set your lat/lon pins for the approximate start and end location of the frame. Longitude does not really matter, as long as it is close to the center of the frame. Latitude is more important. Note, these values are approximate only, and it's a good idea to make them a little bit larger than you really need. Make sure you have downloaded data from an area larger than the extent of your pins, too, or you may get some frames with missing data!

```
direction="D" # D or A
pin1="-106.5/35.4" #lon/lat along northern frame edge
pin2="-106.7/34.9" #lon/lat along southern frame edge
```    
    
3. Finally, the commad is run with the correct options.

```
python $code_path $download_path -o $orbit_path -d $direction -l $pin1/$pin2 -n $nproc
```

Note: You do not need to unzip the data beforehand; this will be done automatically during the frame creation. If you have already unzipped your files, add the additional flag '-z' at the end of the command.
