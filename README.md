Sentinel-1 query and download script
------
Eric Lindsey, Earth Observatory of Singapore

Last updated: June 2020

This repository contains a simple script that enables easy search and download of Sentinel-1 (or other SAR) data hosted at the Alaska Satellite Facility (ASF) using the ASF API. For help on this API, visit https://asf.alaska.edu/api/

The basic use of the script is as follows: enter API keywords and values in a config file (example included), then pass this file as a single argument on the command line. The script will generate an API query, and download the resulting .csv file of results. To download the granules, add the command-line option --download.

Here is a simple example of the config file, which returns IW scenes collected during the first two weeks in April 2019 from Path 18 over Singapore:

    [api_search]
    output = csv
    platform = Sentinel-1A,Sentinel-1B
    processingLevel = SLC
    beamMode = IW
    intersectsWith = POLYGON((103.1197 0.3881,104.5655 0.3881,104.5655 2.263,103.1197 2.263,103.1197 0.3881))
    start=2019-04-01T00:00:00UTC
    end=2019-04-15T00:00:00UTC
    relativeOrbit=18

    [download]
    download_site = both
    nproc = 2

    [asf_download]
    http-user = <username>
    http-password = <password>

Currently, the script is set up to prefer downloading from the AWS Sentinel-1 Public Dataset for Southeast Asia; if no file is found there we fall back to downloading from ASF directly (this requires an ASF account). See the config file for more details on this option, and for more information on the AWS dataset, see https://registry.opendata.aws/sentinel1-slc-seasia-pds/

Running multiple downloads in parallel is now enabled through the python multiprocessing toolbox, via the config file option 'nproc'. The true effective speedup from running many downloads at the same time has not been tested; this may depend on your own storage and bandwidth situation.

