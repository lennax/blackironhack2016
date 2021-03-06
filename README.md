README
======

Travel Risk Evaluation
----------------------

Copyright 2016 Lenna X. Peterson

Contact: lenna.peterson@gmail.com

License: GPL v3

This distribution also includes Tangle.js, which is covered by the MIT license

Keywords
--------
* travel
* relative risk
* vector-borne virus
* mosquito activity

Datasets
--------
* NOAA Climate Normals Monthly
    - http://www.ncdc.noaa.gov/cdo-web/webservices/v2
    - JSON data
    - Normal annual precipitation, temperature, and growing degree day information is used to assess the suitability of the climate for mosquitoes
    - Data is available for the entire US

* Zika Cases Reported in the United States
    - http://www.cdc.gov/zika/intheus/maps-zika-us.html 
    - Table data
    - The number of cases for the corresponding state is used
    - Data is available for the entire US

* 2015 American Community Survey Subject Tables
    - http://www.census.gov/data/developers/data-sets/acs-1yr.html
    - JSON data
    - The population of the corresponding county or state is used
    - Data is available for the entire US

* Compressed Mortality File 1999-2014 on CDC WONDER Online Database
    - http://wonder.cdc.gov/cmf-icd10.html
    - Table data
    - Annual deaths per 1,000,000 in the USA by several causes is used
    - Data is available for the entire US

* Y The primary dataset "online climate data" from data.gov is used

* Y All datasets used are from the US government

Description
-----------
This website provides travelers with information and context about the risk of contracting Zika virus and other mosquito-borne diseases while traveling within the United States.
The user provides their destination and date of travel.
The website shows the destination on a map and estimates the disease risk on that date.

* Map View
    1. Y The map is centered on the travel destination
    2. Y The map has a marker for the travel destination
    3. Y The map has a label for the travel destination
    4. Y The map has an InfoWindow 
    5. N The map does not have additional overlays

* Data Visualization
    1. Y The page uses Plot.ly bar charts to show risk components and a Plot.ly scatter plot to show risk of Zika virus in context of other risks
    2. N The chart has hover but no click interaction

* Interaction Form
    1. Y Information about climate, mosquito activity, and cases of Zika in the state is output
    2. Y The user can drag to change their month of travel and see how it changes mosquito risk
    3. Y The user inputs their date of travel and destination
    4. Y If the user changes the date and destination of travel, the map is updated based on the location
    5. Y If the user changes the date and destination of travel, the charts are updated based on the risk

Build Case
----------
* Dependencies
    - python
    - gunicorn
    - flask
    - numpy
    - beautifulsoup4

* Building

    sudo apt-get install python python-flask python-pip

    sudo pip install -r requirements.txt

* Usage
    1. Start the flask server with `python server.py`
    2. Open Google Chrome and go to 127.0.0.1:5000
    3. Enter data into the form and click 'Submit'

Testing
-------
This website was tested on Ubuntu 14.04 using Google Chrome version 53.0.2785.116
