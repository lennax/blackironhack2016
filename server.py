# -*- coding: utf-8 -*-

# STANDARD LIBRARY
import datetime
from functools import update_wrapper
from ftplib import FTP
import json
import logging
import urllib

# 3RD PARTY LIBRARIES
import numpy as np

from flask import Flask, jsonify, render_template, request, make_response, current_app
# from flask_cors import CORS, cross_origin
from flask.ext.cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)
#app.debug = True

# Only use the FileHandler from gunicorn.error logger
gunicorn_error_handlers = logging.getLogger('gunicorn.error').handlers
app.logger.handlers.extend(gunicorn_error_handlers )
#app.logger.addHandler(myhandler1)
#app.logger.addHandler(myhandler2)
app.logger.info('my info')
app.logger.debug('debug message')

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
    #    destination = request.args.get('destination')
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    mydate = request.args.get('date')
#    print destination
    return jsonify(result=get_result(lat=lat,
                                     lng=lng,
                                     mydate=mydate))

def get_result(lat, lng, mydate):

    latlng = (lat, lng)
    #print latlng
    app.logger.debug(latlng)

    # parse date
    #datefmt = "%m/%d/%Y"
    datefmt = "%Y-%m-%d"
    try:
        parsed_date = datetime.datetime.strptime(mydate, datefmt)
    except ValueError:
        # Server-side input validation
        return dict(error="Invalid date")
    month_number = parsed_date.month
    month_name = parsed_date.strftime("%B")

#    print mydate, month_number, month_name

    # possibly temporarily use zip codes
#    ftp://ftp.ncdc.noaa.gov/pub/data/normals/1981-2010/station-inventories/zipcodes-normals-stations.txt

    # Query NOAA for list of weather stations
    ftp = FTP(open_climate_ftp)
    ftp.login()
    ftp.cwd("/pub/data/normals/1981-2010/")

    station_list = list()
    # Fixed width
    # Columns: ID, lat, long, ??, state 2 letter, name, ???, ???
    ftp.retrlines("RETR station-inventories/allstations.txt",
                  station_list.append)
    coord_array = np.zeros((len(station_list), 2))
    for x, line in enumerate(station_list):
        parts = line.split()
        lat = float(parts[1])
        lon = float(parts[2])
        coord_array[x, 0] = lat
        coord_array[x, 1] = lon

#    print coord_array[:6]

    # Find closest weather station

    # radius of Earth in miles
    earth_radius = 3958.75

    def get_distances(latlng, coord_array):
        "Compute lat/lng distance using Haversine formula"
        latlng = np.deg2rad(latlng)
        coord_array = np.deg2rad(coord_array)

        lat_diff = (coord_array[:, 0] - latlng[0]) * 0.5
        lng_diff = (coord_array[:, 1] - latlng[1]) * 0.5

        np.sin(lat_diff, out=lat_diff)
        np.sin(lng_diff, out=lng_diff)

        np.power(lat_diff, 2, out=lat_diff)
        np.power(lng_diff, 2, out=lng_diff)

        lng_diff *= (np.cos(coord_array[:, 0]) * np.cos(latlng[0]))
        lng_diff += lat_diff

        np.arcsin(np.power(lng_diff, 0.5), out=lng_diff)
        lng_diff *= (2 * earth_radius)

        return lng_diff

    distances = get_distances(latlng, coord_array)
    # Get the index of the smallest distance
    closest_index = np.argpartition(distances, 1)[0]
    closest_row = station_list[closest_index]
    stationid = closest_row.split()[0]

    #print stationid
    app.logger.debug(stationid)

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
    
    temp_risk = None
    rain_risk = None

    # http://www.ncbi.nlm.nih.gov/pmc/articles/PMC4001452/
    # Aedes albopictus is not expected to survive average January temperatures of -5 C (23 F)
#    tenths of degrees Fahrenheit for maximum, minimum, average, dew point, heat
#    index, wind chill, and air temperature normals and standard deviations.
#    e.g., "703" is 70.3F
    tavg_row = get_row("products/temperature/mly-tavg-normal.txt")
    if tavg_row is not None:
        tavg_ints = [int(v[:-1]) * 0.1 for v in tavg_row.split()[1:]]
        jan_temp = tavg_ints[0]
        temp_risk = bool(jan_temp > 23.0)

    # Aedes albopictus requires a minimum annual rainfall of ~250 mm (9.8 inches)
#    tenths of inches for average monthly/seasonal/annual snowfall,
#    month-to-date/year-to-date snowfall, and percentiles of snowfall.
#    e.g. "39" is 3.9"
    rain_row = get_row("products/precipitation/ann-prcp-normal.txt")
    if rain_row is not None:
        rain_in = int(rain_row.split()[1][:-1]) * 0.1
        rain_risk = bool(rain_in >= 9.8)

    if temp_risk and rain_risk:

        cooling_value = None
        # http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3700474/
        # roughly 100 degree days for Culex
        # Cooling degree days are equivalent to growing degree days
        cooling_result = get_row("products/temperature/mly-cldd-base57.txt")
        #    print cooling_result
        if cooling_result is not None:
            cooling_list = cooling_result.split()
            cooling_ints = [int(v[:-1]) if v[0] !=
                            "-" else 0 for v in cooling_list[1:]]
            cumulative_cdd = np.cumsum(cooling_ints)
            #print cumulative_cdd
            app.logger.debug(cumulative_cdd)
            cooling_value = cumulative_cdd[month_number - 1]

        cooling_text = "mosquitoes have likely not yet hatched"
        if cooling_value > 100:
            cooling_text = "mosquitoes have likely hatched"

            # tmin 9.6 C (49.28 F)
            # tmax 37 C (98.6 F)
            # TODO convert to quadratic
            month_temp = tavg_ints[month_number - 1]

            conjunction = "but"
            risk = 1
            if month_temp < 49.28:
                temp_text = "it is too cold for mosquitoes"
            elif month_temp > 98.6:
                temp_text = "it is too hot for mosquitoes"
            else:
                conjunction = "and"
                temp_text = "it is the right temperature for mosquitoes"
                risk = 15

            cooling_text = " ".join([cooling_text, conjunction, temp_text])

        # Aedes aegypti populations are not necessarily rainfall dependent
    #    hundredths of inches for average monthly/seasonal/annual precipitation,
    #    month-to-date/year-to-date precipitation, and percentiles of precipitation.
    #    e.g., "1" is 0.01" and "1486" is 14.86"
#        precip_result = get_row("products/precipitation/mly-prcp-normal.txt")
#    #    print precip_result
#        precip_list = precip_result.split()
#        precip_value = int(precip_list[month_number][:-1]) * 0.01

        result_text = "The climate at your destination is hospitable to mosquitoes. In {month_name}, {cooling_text}.".format(
            cooling_text=cooling_text, month_name=month_name)

        # TODO compute some sort of risk
        risk = 15

    else:
        result_text = "The climate at your destination is not hospitable to mosquitoes."
        risk = 1

    result_dict = dict(text=result_text,
                       risk=risk,
                       error=0)

    return result_dict

if __name__ == "__main__":
    app.run()
