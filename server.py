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
# from flask_cors import CORS, cross_origin
from flask.ext.cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)
app.debug = True

####

open_climate_ftp = "ftp.ncdc.noaa.gov"
#"/pub/data/normals/1981-2010/"

@app.route('/')
def index():
   return render_template('index.html')

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

    def get_row(filename):
        row_list = list()
        ftp.retrlines("RETR {0}".format(filename), row_list.append)
        for line in row_list:
            stnid = line[:11]
            if stnid == stationid:
                return line

    #ftp.retrlines("RETR products/auxiliary/station/{0}-normals.txt".format(stationid))
    
    # http://www.ncbi.nlm.nih.gov/pmc/articles/PMC4001452/
    # Aedes albopictus is not expected to survive average January temperatures of -5 C (23 F)
#    tenths of degrees Fahrenheit for maximum, minimum, average, dew point, heat 
#    index, wind chill, and air temperature normals and standard deviations. 
#    e.g., "703" is 70.3F
    tavg_row = get_row("products/temperature/mly-tavg-normal.txt")
    jan_temp = int(tavg_row.split()[1][:-1]) * 0.1
    temp_risk = bool(jan_temp > 23.0)
    
    # Aedes albopictus requires a minimum annual rainfall of ~250 mm (9.8 inches)
#    tenths of inches for average monthly/seasonal/annual snowfall, 
#    month-to-date/year-to-date snowfall, and percentiles of snowfall. 
#    e.g. "39" is 3.9"
    rain_row = get_row("products/precipitation/ann-prcp-normal.txt")
    rain_in = int(rain_row.split()[1][:-1]) * 0.1
    rain_risk = bool(rain_in >= 9.8)
    
    if temp_risk and rain_risk:
    
        # Cooling degree days are equivalent to growing degree days
        cooling_result = get_row("products/temperature/mly-cldd-base57.txt")
    #    print cooling_result
        cooling_list = cooling_result.split()
        cooling_value = int(cooling_list[month_number][:-1])

    #    hundredths of inches for average monthly/seasonal/annual precipitation, 
    #    month-to-date/year-to-date precipitation, and percentiles of precipitation. 
    #    e.g., "1" is 0.01" and "1486" is 14.86"
        precip_result = get_row("products/precipitation/mly-prcp-normal.txt")
    #    print precip_result
        precip_list = precip_result.split()
        precip_value = int(precip_list[month_number][:-1]) * 0.01
        
    # TODO determine amount of degree days and precipitation needed for mosquitoes
        
        result_text = "The climate at your destination is hospitable to mosquitoes. {month_name} normally has {0} cooling degree days and {1} inches of rain.".format(cooling_value, precip_value, month_name=month_name)
        
    # TODO compute some sort of risk
        risk = 15
    
    else:
        result_text = "The climate at your destination is not hospitable to mosquitoes."
        risk = 1

    result_dict = dict(text=result_text,
                       risk=risk)
    
    return jsonify(result=result_dict)

if __name__ == "__main__":
    app.run()
