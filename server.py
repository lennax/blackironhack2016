# -*- coding: utf-8 -*-

# STANDARD LIBRARY
import datetime
from functools import update_wrapper
from ftplib import FTP
import json
import urllib

# 3RD PARTY LIBRARIES
#import numpy

from flask import Flask, jsonify, render_template, request, make_response, current_app
from flask_cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)
app.debug = True

####

open_climate_ftp = "ftp.ncdc.noaa.gov"
#"/pub/data/normals/1981-2010/"

#@app.route('/')
#def index():
#    return render_template('index2.html')

@app.route('/calculate', methods=['GET', 'OPTIONS'])
def calculate():
#    destination = request.form.get('destination')
#    date = request.form.get('date')
    destination = request.args.get('destination')
    mydate = request.args.get('date')
    print destination
#    print "I like donkeys"
    
    # TODO parse date
    datefmt = "%m/%d/%Y"
    parsed_date = datetime.datetime.strptime(mydate, datefmt)
    month_number = parsed_date.month
    month_name = parsed_date.strftime("%B")
    
#    print mydate, month_number, month_name
    
    # possibly temporarily use zip codes
#    ftp://ftp.ncdc.noaa.gov/pub/data/normals/1981-2010/station-inventories/zipcodes-normals-stations.txt
    
    # TODO Query NOAA for list of weather stations
    ftp = FTP(open_climate_ftp)
    ftp.login()
    ftp.cwd("/pub/data/normals/1981-2010/")
    station_list = list()
    # Fixed width
    # Columns: ID, lat, long, ??, state 2 letter, name, ???, ???
    #ftp.retrlines("station-inventories/allstations.txt", station_list.append)
    # Space separated
    # Columns:  ID, zip code, city
    ftp.retrlines("RETR station-inventories/zipcodes-normals-stations.txt", station_list.append)

    stationid = None
    for line in station_list:
        parts = line.split()
#        print destination, parts[1], destination == parts[1]
        if parts[1] == destination:
#            print "storing"
            stationid = parts[0]
            break
    print stationid
    
    # TODO Find closest weather station
    #distances = scipy.spatial.cdist(my_loc, station_loc)
    #closest = np.partition(distances, 1)[0]
    # or mydf.nsmallest(1)
    
    # TODO Get month data for that weather station
#        1. Long-term averages of monthly precipitation totals:
#  	  mly-prcp-normal.txt
#       2. The average number of days per month with snowfall greater than 1 inch:
#          mly-snow-avgnds-ge010ti.txt
#       3. Daily average base-65 heating degree days:
#          dly-htdd-normal.txt.
#       4. Daily average base-50 heating degree days:
#          dly-htdd-base50.txt
#       5. Hourly heat index normals:
#          hly-hidx-normal.txt  

#       Variable  Columns  Type
#       ----------------------------
#       STNID       1- 11  Character
#       VALUE1     19- 23  Integer
#       FLAG1      24- 24  Character
#       - - - - - - - - - - - - - -
#       VALUE12    96-100  Integer
#       FLAG12    101-101  Character
#       ----------------------------
#
#       These variables have the following definitions:
#
#       STNID   is the GHCN-Daily station identification code.
#       VALUE1  is the January value.
#       FLAG1   is the completeness flag for January. See Flags section below.
#       - - - -
#       Value12 is the December value.
#       Flag12  is the completeness flag for December.


    #ftp.retrlines("RETR products/auxiliary/station/{0}-normals.txt".format(stationid))
    
    # Cooling degree days are equivalent to growing degree days
    cooling_list = list()
    ftp.retrlines("RETR products/temperature/mly-cldd-base57.txt", cooling_list.append)
    
    cooling_result = None
    for line in cooling_list:
        stnid = line[0:11]
        #print stationid, stnid, stnid == stationid
        if stnid == stationid:
            cooling_result = line
#    print cooling_result
    cooling_list = cooling_result.split()
    cooling_value = int(cooling_list[month_number][:-1])
    
#    hundredths of inches for average monthly/seasonal/annual precipitation, 
#    month-to-date/year-to-date precipitation, and percentiles of precipitation. 
#    e.g., "1" is 0.01" and "1486" is 14.86"

    precip_list = list()
    ftp.retrlines("RETR products/precipitation/mly-prcp-normal.txt", precip_list.append)
    
    precip_result = None
    for line in precip_list:
        stnid = line[0:11]
        #print stationid, stnid, stnid == stationid
        if stnid == stationid:
            precip_result = line
#    print precip_result
    precip_list = precip_result.split()
    precip_value = int(precip_list[month_number][:-1])
    
    result_text = "At your destination, {month_name} normally has {0} cooling degree days and {1} inches of rain".format(cooling_value, precip_value * 0.01, month_name=month_name)
    
    result_dict = dict(text=result_text,
                       risk="low")
    
    # TODO determine amount of degree days and precipitation needed for mosquitoes
    
    return jsonify(result=result_dict)

if __name__ == "__main__":
    app.run()
