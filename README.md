Sentinel-1 query and download script
------
Ted Li, Virginia Tech
July 2024

Modified sentinel_query_download.py from Eric Lindsey.
Everything else remains the same.


sentinel_query_download.py
------

Changes I made: 

The script now also takes in arguments to change certain parameters so we don't have to manually change the .config file. Also, the intersectsWith parameter is computed with entering a single Lat and Long coordinate for ease of use and a small polygon is inputed for the search query. (For some reason the Area of Interest Point does not work in ASF so this is my workaround)

Most importantly I noticed a previous issue (https://github.com/ericlindsey/sentinel_query_download/issues/2)
about the wget function not working and needing to manually put in the wget into the command line. 
This is a problem with python: (https://www.google.com/search?client=firefox-b-1-d&q=wget+problem+in+python) 
so I used downloadGranule_url instead to download the files successfully straight from the script.

Also logs the amount of time needed to query, download and unzip the image files.

Additionally, I changed the download directory structure to be cwd/satellite(dataset)/GUID/unzipped contents. I think this makes it more intuitive rather than the Granule Name.

    
```

Note: You do not need to unzip the data beforehand; this will be done automatically during the frame creation. If you have already unzipped your files, add the additional flag '-z' at the end of the command.
