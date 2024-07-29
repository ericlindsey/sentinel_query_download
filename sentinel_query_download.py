#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use ASF API to search for granules given search parameters found in a config file.
Then generate URL and download from either AWS open dataset or ASF.

First version: October 2017
Modified April 2019 to include AWS downloading
Modified June 2019 to enable parallel downloads
Modified Oct 2019 to enable multiple file types (e.g. csv,json,kml)
Modified July 2021, minor fixes
Modified April 2023, change multiprocessing start method to spawn to avoid race conditions
Modified July 2024, download through url

@author: Eric Lindsey, University of New Mexico
"""

import configparser, argparse, requests, csv, subprocess, os, multiprocessing, time, sys, zipfile, requests
import urllib.request, shutil, uuid
from urllib.error import HTTPError, URLError
import PIL
from PIL import Image
import numpy as np
import glob
import sqlite3

# optional use urllib instead of wget
# from urllib.request import urlopen

# hard-coded ASF query URL:
asf_baseurl = "https://api.daac.asf.alaska.edu/services/search/param?"

# hard-coded AWS base URL for public dataset downloads:
aws_baseurl = (
    "http://sentinel1-slc-seasia-pds.s3-website-ap-southeast-1.amazonaws.com/datasets/slc/v1.1/"
)


def downloadGranule(row, args_dict, GUID_dir):
    orig_dir = os.getcwd()
    download_site = row["Download Site"]
    frame_dir = "P" + row["Path Number"].zfill(3) + "/F" + row["Frame Number"].zfill(4)

    satellite_dir = args_dict["dataset"]
        
    sub_dir = args_dict["start"] + "/" + args_dict["end"]

    download_dir = os.path.join(satellite_dir, sub_dir)
    # Setting up the directory structure:
    flag = os.path.exists(satellite_dir)

    if not flag:
        os.makedirs(satellite_dir, exist_ok=True)
        print("Existing parent dir: ", satellite_dir)
    # elif not flag:
    #     os.makedirs(satellite_dir, exist_ok=True)
    #     os.makedirs(download_dir, exist_ok=True)
    #     print("Had to create parent dir: ", satellite_dir)

    print("Downloading granule ", row["Granule Name"], "to directory", frame_dir)
    # create frame directory

    status = 0
    if download_site == "AWS" or download_site == "both":
        print("Try AWS download first.")
        # create url for AWS download, based on the granule name
        row_date = row["Acquisition Date"]
        row_year = row_date[0:4]
        row_month = row_date[5:7]
        row_day = row_date[8:10]
        datefolder = row_year + "/" + row_month + "/" + row_day + "/"
        aws_url = (
            aws_baseurl + datefolder + row["Granule Name"] + "/" + row["Granule Name"] + ".zip"
        )
        # run the download command
        status = 0
        # DEBUGGING COMMENTED OUT
        # downloadGranule_wget(aws_url)
        if status != 0:
            if download_site == "AWS":
                print("AWS download failed. Granule not downloaded.")
            else:
                print("AWS download failed. Trying ASF download instead.")
    if (status != 0 and download_site == "both") or download_site == "ASF":
        asf_url = row["asf_wget_str"] + " " + row["URL"]
        # run the download command
        # status = downloadGranule_wget(asf_url) DEBUGGING COMMENTED OUT

        options = row["asf_wget_str"].split()
        for option in options:
            if option.startswith('--http-user='):
                asf_user = option.split('=')[1]
            elif option.startswith('--http-password='):
                asf_pass = option.split('=')[1]

        downloadGranule_url(row["URL"], asf_user, asf_pass)

        if status != 0:
            print("ASF download failed. Granule not downloaded.")

        if status == 0:
            zip_file = row["Granule Name"] + ".zip"
            
            #Below is to make directory structure of Satellite/Acquisition Date/metadata
            #renamed_directory = row["Acquisition Date"][:10]
            #destination_dir = os.path.join(satellite_dir, renamed_directory)
            
            #Below to make directory structure of Satellite/GUID/metadata
            # satellite_dir = config.get("api_search", "dataset")
            # GUID_dir = os.path.join(satellite_dir, str(uuid.uuid4()))

            #Extract all contents into the GUID_dir
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(GUID_dir)

            extracted_dirs = [name for name in os.listdir(GUID_dir) if os.path.isdir(os.path.join(GUID_dir, name))]
            dir_path = os.path.join(GUID_dir, extracted_dirs[0])
            
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                for item in os.listdir(dir_path):
                    shutil.move(os.path.join(dir_path, item), GUID_dir)
                
                os.rmdir(dir_path)

            os.remove(zip_file)

    os.chdir(orig_dir)


## urllib not currently used. Test for speed?
# def downloadGranule_urllib(url):
#    fzip = url.split('/')[-1]
#    if os.path.isfile(fzip) == False:
#        print("Using python urllib to download "+url+" to file "+fzip)
#        with urlopen(url) as response, open(fzip, 'wb') as ofile:
#            shutil.copyfileobj(response, ofile)
#    return 0

def downloadGranule_url(url, username, password):
    print("URL: ", url," USER: ", username, " PASS :", password)
    with requests.Session() as s:
        s.auth = (username, password)
        # Get the redirection URL: Notice the use of requests and not the session
        r1 = requests.get(url) 
        r = s.get(r1.url, allow_redirects=True)
        # Define the filename
        filename = url.split("/")[-1]

        if r.status_code == 200:
            with open(filename, "wb") as f:
                f.write(r.content)
            print(f"Downloaded '{filename}' successfully!")

            # Verify if the file exists and has content
            if os.path.isfile(filename) and os.path.getsize(filename) > 0:
                print(f"File '{filename}' exists and is not empty.")
            else:
                print(f"File '{filename}' is empty or does not exist.")
        else:
            print(f"Failed to download: HTTP {r.status_code}")


def chop_array(array, chip_size):
    # Break apart array into smaller arrays ("chips") of size chip_size x chip_size
    chips = []
    num_rows, num_cols = array.shape

    for i in range(0, num_rows, chip_size):
        for j in range(0, num_cols, chip_size):
            chip = array[i : i + chip_size, j : j + chip_size]
            chips.append(chip)

    return chips


if __name__ == "__main__":
    
    
    # read command line arguments and parse config file.
    parser = argparse.ArgumentParser(
        description="Use http requests and wget to search and download data from the ASF archive, based on parameters in a config file."
    )

    parser.add_argument(
        "config", type=str, help="supply name of config file to set up API query. Required."
    )
    parser.add_argument(
        "--download", action="store_true", help="Download the resulting scenes (default: false)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the query result to the screen (default: false)",
    )
    # ADDED LINES ~~~~~~~~~~~~~~~~~~~
    parser.add_argument("--processingLevel", type=str, help="Level or processing")
    parser.add_argument(
        "--dataset", type=str, help="What type of dataset: e.g. Sentinel-1, OPERA-S1, etc"
    )
    parser.add_argument(
        "--beamSwath",
        type=str,
        help="Beam mode used to acquire the data, specify a single value or a list",
    )
    parser.add_argument("--polarization", type=str, help="SAR waves used to extract the data")
    parser.add_argument(
        "--intersectsWith", type=str, help="Longitude and Latitude in floats, Format: X,Y"
    )
    parser.add_argument("--start", type=str, help="Starting date and time, Format: YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="Ending date and time, Format: YYYY-MM-DD")
    parser.add_argument("--username", type=str, help="ASF Username")
    parser.add_argument("--password", type=str, help="ASF Password")

    parser.add_argument("--prediction", type=str, help="Boolean: Whether or not we'll make a prediction on flooding")

    args = parser.parse_args()

    # read config file
    config = configparser.ConfigParser()
    config.optionxform = str  # make the config file case-sensitive
    config.read(args.config)
    download_site = config.get("download", "download_site", fallback="both")
    nproc = config.getint("download", "nproc", fallback=1)
    output_format = config.get("api_search", "output", fallback="csv")
    
    satellite_dir = config.get("api_search", "dataset")
    GUID_dir = os.path.join(satellite_dir, str(uuid.uuid4()))


    # Update config only if arguments are provided
    if args.processingLevel is not None:
        config.set("api_search", "processingLevel", args.processingLevel)

    if args.dataset is not None:
        config.set("api_search", "dataset", args.dataset)

    if args.beamSwath is not None:
        config.set("api_search", "beamSwath", args.beamSwath)

    if args.polarization is not None:
        config.set("api_search", "polarization", args.polarization)

    if args.start is not None:
        config.set("api_search", "start", args.start)

    if args.end is not None:
        config.set("api_search", "end", args.end)

    if args.username is not None:
        config.set("asf_download", "http-user", args.username)

    if args.password is not None:
        config.set("asf_download", "http-password", args.password)

    if args.prediction is not None:
        config.set("prediction", "prediction", args.prediction)

    if args.intersectsWith is not None:
        coor_list = [float(num) for num in args.intersectsWith.split(",")]
        polygon_coor = [
            [coor_list[0], coor_list[1]],
            [coor_list[0] + 0.01, coor_list[1]],
            [coor_list[0] + 0.01, coor_list[1] + 0.01],
            [coor_list[0], coor_list[1]],
        ]
        polygon_str = ",".join([" ".join(map(str, sublist)) for sublist in polygon_coor])
        finished_str = "POLYGON((" + polygon_str + "))"
        config.set("api_search", "intersectsWith", finished_str)

    with open("sentinel_query.config", "w") as configfile:
        config.write(configfile)

    # we parse the config options directly into a query... this may be too naive
    arg_list = config.items("api_search")

    config.read('sentinel_query.config')

    command_line_args = {}

    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            arg = arg[2:]

        if "=" in arg:
            key, value = arg.split("=")
            if key == "intersectsWith":
                command_line_args[key] = finished_str
            else:
                command_line_args[key] = value
        else:
            command_line_args[arg] = True

    for section in config.sections():
        for key, value in config.items(section):
            if key not in command_line_args:
                command_line_args[key] = value

    command_line_url = "&".join("%s=%s" % (key, value) for key, value in command_line_args.items())

    # join as a single argument string
    arg_str = "&".join("%s=%s" % (item[0], item[1]) for item in arg_list)
    # form into a query

    new_arg_str = arg_str.replace("+", "%2B")

    argurl = asf_baseurl + new_arg_str
    commandurl = asf_baseurl + command_line_url
    print("COMMANDLINE URL: ", commandurl + "\n")
    print(argurl)
    # example query:
    # argurl="https://api.daac.asf.alaska.edu/services/search/param?platform=R1\&absoluteOrbit=25234\&output=CSV"

    # run the ASF query request
    print("\nRunning ASF API query:")
    print(argurl + "\n")

    start_time = time.time()

    r = requests.post(argurl)
    # parse rows if csv, else we just operate on the 'r' object
    if output_format == "csv":
        reader = csv.DictReader(r.text.splitlines())
        rows = list(reader)



    # save the results to a file
    logtime = time.strftime("%Y_%m_%d-%H_%M_%S")
    query_log = "asf_query_%s.%s" % (logtime, output_format)
    with open(query_log, "w") as f:
        print("Query result saved to asf_query_%s.%s" % (logtime, output_format))
        f.write(r.text)
        

    # print the results to the screen
    if args.verbose:
        if output_format == "csv":
            # print the results in a nice format
            numscenes = len(rows)
            plural_s = "s" if numscenes > 1 else ""
            if numscenes > 0:
                print("Found %s scene%s." % (numscenes, plural_s))
                # for row in rows:
                #     print("DEBUGGING")
                #     print(row)
                #     print(
                #         "Scene %s, Path %s / Frame %s"
                #         % (row["Granule Name"], row["Path Number"], row["Frame Number"])
                #     )
        else:
            print(r.text)

    # If a download is requested:
    # parse result into a list of granules, figure out the correct path, and download each one.
    if output_format != "csv" and args.download:
        print("Error: cannot download unless output format is set to csv. Doing nothing.")
    if output_format == "csv" and args.download:
        if nproc > 1:
            print("\nRunning %d downloads in parallel." % nproc)
        else:
            print("\nDownloading 1 at a time.")
        # need to pass http-user and http-password for ASF downloads.
        # this section should contain 'http-user', 'http-password', plus any other wget options.
        # we join them (naively) as a single argument string
        if download_site != "AWS":
            # first, check for missing values:
            if not (
                config.has_section("asf_download")
                and config.has_option("asf_download", "http-user")
                and config.has_option("asf_download", "http-password")
                and len(config.get("asf_download", "http-user")) > 0
                and len(config.get("asf_download", "http-password")) > 0
            ):
                raise ValueError("ASF username or password missing in config file.")
            asf_wget_options = config.items("asf_download")
            asf_wget_str = " ".join("--%s=%s" % (item[0], item[1]) for item in asf_wget_options)

        else:
            asf_wget_str = ""
        downloadList = []
        for row in rows:
            downloadDict = row
            # add some extra info to the csv row for download purposes
            downloadDict["Download Site"] = download_site
            downloadDict["asf_wget_str"] = asf_wget_str
            downloadList.append(downloadDict)
        # map list to multiprocessing pool
        
        multiprocessing.set_start_method("spawn")
        with multiprocessing.get_context("spawn").Pool(processes=nproc) as pool:
            pool.starmap(
                downloadGranule, [(row, command_line_args, GUID_dir) for row in downloadList], chunksize=1
            )
            # pool.map(downloadGranule, downloadList, chunksize=1)
        print("\nDownload complete.\n")
        end_time = time.time()
        elapsed_time = end_time-start_time
        print(f"Total time taken to query and download image files: {elapsed_time:.2f} seconds")
    else:
        print("\nNot downloading.\n")

            

    print("Sentinel query complete.\n")
