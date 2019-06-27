Sentinel-1 query and download script
------
Eric Lindsey, Earth Observatory of Singapore

Last updated: June 2019

This repository contains a simple script that enables easy search and download of Sentinel-1 data using the ASF API. For help on this API, visit https://www.asf.alaska.edu/get-data/learn-by-doing/

The basic use of the script is as follows: enter API keywords and values in a config file (example included), then pass this file as a single argument on the command line. The script will generate an API query, and download the resulting .csv file of results. To download the granules, add the command-line option --download.

Currently, the script is set up to prefer downloading from the AWS Sentinel-1 Public Dataset for Southeast Asia; if no file is found there it the script falls back to downloading from ASF directly. For more information on the AWS dataset, see https://registry.opendata.aws/sentinel1-slc-seasia-pds/

Running multiple downloads in parallel is now enabled through python multiprocssing, via the config file option 'nproc'. The true effective speedup from running many downloads at the same time has not been tested; this may depend on your own storage and bandwidth situation.

