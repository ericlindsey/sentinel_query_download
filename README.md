Sentinel-1 query and download script
------
Eric Lindsey, Earth Observatory of Singapore

Last updated: June 2020

This repository contains a simple script that enables easy search and download of Sentinel-1 (or other SAR) data hosted at the Alaska Satellite Facility (ASF) using the ASF API. For help on this API, visit https://www.asf.alaska.edu/get-data/learn-by-doing/

The basic use of the script is as follows: enter API keywords and values in a config file (example included), then pass this file as a single argument on the command line. The script will generate an API query, and download the resulting .csv file of results.

The default is to return a search query (csv file) but not download the data. To download the granules after searching, add the command-line option --download. To print out a human-readable table of the results to the screen, use --verbose.

Here is a simple config file example, which returns IW scenes collected during the first two weeks in April 2019 from Path 56 over Albuquerque, NM:

    [api_search]
    output = csv
    platform = Sentinel-1A,Sentinel-1B
    processingLevel = SLC
    beamMode = IW
    intersectsWith = POLYGON((-106.7975 34.9141,-106.3267 34.9141,-106.3267 35.3502,-106.7975 35.3502,-106.7975 34.9141))
    start=2019-04-01T00:00:00UTC
    end=2019-04-15T00:00:00UTC
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

Currently, the script is set up to prefer downloading from the AWS Sentinel-1 Public Dataset for Southeast Asia; if no file is found there we fall back to downloading from ASF directly (this requires an ASF account). See the config file for more details on this option, and for more information on the AWS dataset, see https://registry.opendata.aws/sentinel1-slc-seasia-pds/

Running multiple downloads in parallel is possible through the python multiprocessing toolbox, via the config file option 'nproc'. The true effective speedup from running many downloads at the same time has not been tested; this may depend on your own storage and bandwidth situation.

