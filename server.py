# -*- coding: utf-8 -*-

# STANDARD LIBRARY
import datetime
from functools import update_wrapper
from ftplib import FTP
import json
import logging
import unicodedata
import urllib2

# 3RD PARTY LIBRARIES
from bs4 import BeautifulSoup
import numpy as np

from flask import Flask, jsonify, render_template, request, make_response, current_app
# from flask_cors import CORS, cross_origin
from flask.ext.cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)
app.debug = True

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
zika_url = "http://www.cdc.gov/zika/intheus/maps-zika-us.html"
census_api_key = "36a6a8b2ee9eafcc4afb7f7948e2724907c628e3"
census_url = "http://api.census.gov/data/2015/acs1"


#@app.before_first_request
#def setup_logging():
    #if not app.debug:
        ## In production mode, add log handler to sys.stderr.
        #app.logger.addHandler(logging.StreamHandler())
        #app.logger.setLevel(logging.INFO)

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
    state = request.args.get('state')
    county = request.args.get('county')
#    print destination
    kwargs = dict(lat=lat,
                  lng=lng,
                  mydate=mydate,
                  state=state,
                  county=county)
    return jsonify(result=get_result(**kwargs))

def get_result(lat, lng, mydate, state=None, county=None):

    result_dict = dict(text=None,
                       risk=None,
                       zcases=None,
                       error=0)
  
    latlng = (lat, lng)
    #print latlng
    app.logger.debug(latlng)

    # parse date
    datefmt = "%Y-%m-%d"
    try:
        parsed_date = datetime.datetime.strptime(mydate, datefmt)
    except ValueError:
        # Server-side input validation
        result_dict['error'] = 'Invalid date'
        return result_dict
    month_number = parsed_date.month
    month_name = parsed_date.strftime("%B")

#    print mydate, month_number, month_name

    app.logger.debug(state)
    cases = None
    pop_sentence = None
    if state is not None:
        app.logger.debug("getting zika data")
        zika_data = get_zika()
        for row in zika_data[1:]:
            app.logger.debug("{0} {1} {2}".format(row[0], state, state.lower() == row[0].lower()))
            if state.lower() == row[0].lower():
                cases = row[1] + row[2]

        pop_dict = get_population(state=state, county=county)
        if pop_dict['error'] is None:
            if county is not None and pop_dict['county_pop'] is not None:
                pop_sentence = "{0}, {1} has {county_pop} residents.".format(county, state, **pop_dict)
            elif pop_dict['state_pop'] is not None:
                pop_sentence = "{0} has {state_pop} residents.".format(state, **pop_dict)

    climate_dict = get_climate(latlng=latlng,
                               month_number=month_number,
                               month_name=month_name) 
    if climate_dict['error']:
        return climate_dict
    else:
        result_dict.update(climate_dict)

    result_text = result_dict['text']
    risk = result_dict['risk']

    # TODO handle missing data classes better
    if state is not None and cases is not None:
        result_text += " {0} total cases of Zika have been reported in {1}.".format(cases, state)
        # TODO logistic function
        risk = min(100, risk * 2)

    if pop_sentence is not None:
        result_text = result_text + " " + pop_sentence

    result_dict['text'] = result_text
    result_dict['risk'] = risk

    return result_dict

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

def get_climate(latlng, month_number, month_name):

    result_dict = dict(text=None,
                       risk=None,
                       error="")

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
    else:
        result_dict['error'] += " No monthly average temperature found."

    # Aedes albopictus requires a minimum annual rainfall of ~250 mm (9.8 inches)
    #    tenths of inches for average monthly/seasonal/annual snowfall,
    #    month-to-date/year-to-date snowfall, and percentiles of snowfall.
    #    e.g. "39" is 3.9"
    rain_row = get_row("products/precipitation/ann-prcp-normal.txt")
    if rain_row is not None:
        rain_in = int(rain_row.split()[1][:-1]) * 0.1
        rain_risk = bool(rain_in >= 9.8)
    else:
        result_dict['error'] += " No annual precipitation found."

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
        else:
            result_dict['error'] += " No cooling degree data found."

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

    result_dict['text'] = result_text
    result_dict['risk'] = risk
    return result_dict

def get_zika():
    html_doc = urllib2.urlopen(zika_url)

    soup = BeautifulSoup(html_doc, "html.parser")

    table = soup.body.find("div", id="content").table

    def clean_text(text):
        for repl in "\n", u"\u2020", "*":
            text = text.replace(repl, " ")
        text = text.strip()
        if text:
            return unicodedata.normalize("NFKD", text)

    def process_row(row):
        for x in 1, 2:
            row[x] = int(row[x].split()[0].replace(",", ""))
        return row

    data = list()

    header_cols = table.thead.find_all("th")
    header_cols = [clean_text(ele.text) for ele in header_cols]
    data.append(header_cols)

    for row in table.tbody.find_all('tr'):
        cols = row.find_all('td')
        cols = [clean_text(ele.text) for ele in cols]
        if cols and not all(c is None for c in cols):
            data.append(process_row(cols))

    return data

def get_population(state=None, county=None):
    result = dict(error=None,
                  state_pop=None,
                  county_pop=None)

    if state is None:
        result['error'] = "No population data available."
        return result

    kwargs = dict(key=census_api_key)
    state_param = "?get=NAME,B01001_001E&for=state:*&key={key}".format(**kwargs)
    state_url = census_url + state_param
    
    state_data = json.load(urllib2.urlopen(state_url))
    header = state_data[0]
    name_index = header.index("NAME")
    pop_index = header.index("B01001_001E")
    number_index = header.index("state")

    state_number = None
    for row in state_data[1:]:
        if row[name_index].lower() == state.lower():
            if county is None:
                result['state_pop'] = row[pop_index]
                return result
            else:
                state_number = row[number_index]
                break

    if state_number is not None and county is not None:
        county_param = "?get=NAME,B01001_001E&for=county:*&in=state:{state}&key={key}".format(state=state_number, **kwargs)
        county_url = census_url + county_param
        county_handle = urllib2.urlopen(county_url)
        try:
            county_data = json.load(county_handle)
        except Exception:
            app.logger.debug(county_url)
            raise

        c_header = county_data[0]
        c_name_index = c_header.index("NAME")
        c_pop_index = c_header.index("B01001_001E")
        for row in county_data[1:]:
            if row[c_name_index].lower().startswith(county.lower()):
                result['county_pop'] = row[c_pop_index]
                return result

    return result

if __name__ == "__main__":
    app.run()
