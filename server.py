# -*- coding: utf-8 -*-
# Copyright 2016 Lenna X. Peterson
# This file is part of Travel Risk Evaluation.
#
# Travel Risk Evaluation is free software: you can redistribute it 
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of 
# the License, or (at your option) any later version.
#
# Travel Risk Evaluation is distributed in the hope that it will 
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Travel Risk Evaluation.
# If not, see <http://www.gnu.org/licenses/>.

# STANDARD LIBRARY
import datetime
import json
import logging
import unicodedata
import urllib2

# 3RD PARTY LIBRARIES
from bs4 import BeautifulSoup
import numpy as np
import requests

from flask import Flask, jsonify, render_template, request
app = Flask(__name__)
app.debug = False

# Only use the FileHandler from gunicorn.error logger
gunicorn_error_handlers = logging.getLogger('gunicorn.error').handlers
app.logger.handlers.extend(gunicorn_error_handlers )
app.logger.info('my info')
app.logger.debug('debug message')

####


climate_url = "http://www.ncdc.noaa.gov/cdo-web/api/v2/"
climate_token = "yUvXbVJaOILecTHUTEUEppAxSxHavTJy"
climate_headers = dict(token=climate_token)

zika_url = "http://www.cdc.gov/zika/intheus/maps-zika-us.html"

census_api_key = "36a6a8b2ee9eafcc4afb7f7948e2724907c628e3"
census_url = "http://api.census.gov/data/2015/acs1"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_pop', methods=['GET', 'OPTIONS'])
def get_pop():

    state = request.args.get('state')
    county = request.args.get('county')

    result_dict = dict(instatepop=None,
                       deststatepop=None,
                       incountypop=None,
                       destcountypop=None,
                       popsummary=None,
                       error=None)

    errors = list()
    if not state:
        errors.append('state not specified')

    if errors:
        msg = ", ".join(errors)
        return jsonify(result=dict(error=msg))

    pop_dict = get_population(state=state, county=county)
    if pop_dict['error']:
        errors.append(pop_dict['error'])
    in_pop_dict = get_population(state="indiana", county="tippecanoe")
    if pop_dict['error']:
        errors.append(in_pop_dict['error'])

    inloc = "Indiana"
    destination = state
    pop = pop_dict['state_pop']
    inpop = in_pop_dict['state_pop']
    if county:
        inloc = "Tippecanoe County, Indiana"
        destination = "{0}, {1}".format(county, state)
        pop = pop_dict['county_pop']
        inpop = in_pop_dict['county_pop']

    popsummary = "No population comparison was available. In general, traveling to a less populous area may reduce your risk."
    if pop is not None and inpop is not None:
        popratio = pop * 1.0 / inpop
        if popratio > 2:
            popsummary = "{destination} is more populous than {inloc}. You could reduce your risk by traveling to a less populous area."
        elif popratio < 0.5:
            popsummary = "{destination} is less populous than {inloc}. This may reduce your risk."
        else:
            popsummary = "{destination} and {inloc} have similar populations. You could reduce your risk by traveling to a less populous area."

    result_dict['instatepop'] = in_pop_dict['state_pop']
    result_dict['incountypop'] = in_pop_dict['county_pop']
    result_dict['deststatepop'] = pop_dict['state_pop']
    result_dict['destcountypop'] = pop_dict['county_pop']
    result_dict['popsummary'] = popsummary.format(destination=destination, inloc=inloc)
    if errors:
        result_dict['error'] = ", ".join(errors)

    return jsonify(result=result_dict)

@app.route('/get_cases', methods=['GET', 'OPTIONS'])
def get_cases():
    state = request.args.get('state')

    result_dict = dict(incases=None,
                       destcases=None,
                       casesummary=None,
                       error=None)

    errors = list()
    if not state:
        errors.append('state not specified')

    if errors:
        msg = ", ".join(errors)
        return jsonify(result=dict(error=msg))

    cases = None
    incases = None
    app.logger.debug("getting zika data")
    def add_zika_row(row):
        case1 = row[1]
        case2 = row[2]
        try:
            case1 = int(case1)
            case2 = int(case2)
        except (ValueError, TypeError):
            app.logger.error("Invalid cases number")
        else:
            return case1 + case2
    zika_data = get_zika()
    for row in zika_data[1:]:
        app.logger.debug("{0} {1} {2} {3} ".format(row[0], state, state.lower() == row[0].lower(), row[0].lower() == "indiana"))
        if row[0].lower() == state.lower():
            cases = add_zika_row(row)
        if row[0].lower() == "indiana":
            incases = add_zika_row(row)
    if cases is None:
        errors.append("No case data was found for %s." % state)

    casesummary = "No case comparison was available. In general, traveling to an area with fewer cases may reduce your risk."
    if cases is not None and incases is not None:
        caseratio = cases * 1.0 / incases
        if caseratio > 2:
            casesummary = "{state} has more cases of Zika virus than Indiana. You could reduce your risk by traveling to an area with fewer cases."
        elif caseratio < 0.5:
            casesummary = "{state} has fewer cases of Zika virus than Indiana. This may reduce your risk."
        else:
            casesummary = "{state} and Indiana have similar numbers of Zika virus cases. You could reduce your risk by traveling to an area with fewer cases."

    result_dict['incases'] = incases
    result_dict['destcases'] = cases
    result_dict['casesummary'] = casesummary.format(state=state)
    if errors:
        result_dict['error'] = ", ".join(errors)

    return jsonify(result=result_dict)

@app.route('/get_climate', methods=['GET', 'OPTIONS'])
def get_climate():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    month_no = request.args.get('date', type=int)
    
    result_dict = dict(destclimaterisk=None,
                       destclimate_arr=None,
                       inclimate_arr=None,
                       error=None)

    errors = list()
    # parse date
    if month_no < 0 or month_no > 11:
        errors.append('invalid month')

    if errors:
        msg = ", ".join(errors)
        return jsonify(result=dict(error=msg))

    # Are mosquitoes active in the destination?
    # Is it mosquito season?
    try:
        climate_dict = get_climate_data(latlng=(lat, lng))
    except Exception:
        app.logger.debug(lat)
        app.logger.debug(type(lat))
        app.logger.debug(lng)
        app.logger.debug(type(lng))
        raise
    if climate_dict['error']:
        errors.append(climate_dict['error'])

    in_climate_dict = get_climate_data(latlng=(40.4237, -86.9212))
    if in_climate_dict['error']:
        errors.append(in_climate_dict['error'])

    # Truth table
    #mosquito_risk   mosquito_season risk
    #True    None    unknown
    #None    None    unknown
    #True    True    in season
    #None    True    in season
    #True    False   out of season
    #None    False   out of season
    #False   False   minimal
    #False   True    minimal
    #False   None    minimal

    def parse_risk(mosquito_risk, mosquito_season, **kwargs):
        if mosquito_risk is None or mosquito_risk:
            if mosquito_season is None:
                # If mosquito season is unknown, overall risk is unknown
                return 1
            elif mosquito_season[month_no]:
                # Mosquito season is risk
                return 3
            else:
                # Not mosquito season reduces risk
                return 2
        else:
            # No mosquito risk
            return 0

    mosquito_risk = parse_risk(**climate_dict)
    risk_arr = None
    if climate_dict['mosquito_season'] is not None:
        risk_arr = [int(v) for v in climate_dict['mosquito_season']]

    inclimate_arr = None
    if in_climate_dict['mosquito_season'] is not None:
        inclimate_arr = [int(v) for v in in_climate_dict['mosquito_season']]

    result_dict['destclimaterisk'] = mosquito_risk
    result_dict['destclimate_arr'] = risk_arr
    result_dict['inclimate_arr'] = inclimate_arr

    if errors:
        result_dict['error'] = ", ".join(errors)

    return jsonify(result=result_dict)

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

def get_climate_data(latlng):

    # Are mosquitoes active in the destination?
    # Is it mosquito season?
    result_dict = dict(mosquito_risk=None,
                       mosquito_season=None,
                       error="")

    datatypes = ["MLY-TAVG-NORMAL", "MLY-PRCP-NORMAL", "MLY-GRDD-BASE57"]

    lat, lng = latlng
    extent = [lat - 0.5, lng - 0.5, lat + 0.5, lng + 0.5]

    r = requests.get(climate_url + "stations", headers=climate_headers, params=dict(extent=",".join(str(x) for x in extent), datatypeid=datatypes))

    if r.status_code != 200:
        result_dict['error'] = "error getting stations"
        return result_dict

    result_json = r.json()

    if not result_json:
        result_dict['error'] = "no station results"
        return result_dict

    station_list = result_json['results']
    coord_array = np.zeros((len(station_list), 2))
    for x, line in enumerate(station_list):
        coord_array[x, 0] = line['latitude']
        coord_array[x, 1] = line['longitude']

    distances = get_distances(latlng, coord_array)
    # Get the index of the smallest distance
    closest_index = np.argpartition(distances, 1)[0]
    closest_row = station_list[closest_index]
    stationid = closest_row['id']
    datefmt = "%Y-%m-%d"
    data_date = datetime.datetime.strptime(closest_row['maxdate'], datefmt)
    start_date = data_date - datetime.timedelta(days=365*10)
    start_date = start_date.strftime(datefmt)

    r = requests.get(climate_url + "data", headers=climate_headers,
                     params=dict(
                         stationid=stationid,
                         startdate=start_date,
                         enddate=closest_row['maxdate'],
                         datasetid=["NORMAL_MLY"],
                         datatypeid=datatypes,
                         limit=36,
                         includemetadata="false",
                         )
                    )

    #(YYYY-MM-DDThh:mm:ss)
    datetimefmt = datefmt + "T%H:%M:%S"

    if r.status_code != 200:
        result_dict['error'] = "error getting station data"
        return result_dict
    
    result_json = r.json()
    if not result_json:
        result_dict['error'] = "no station data results"
        return result_dict

    data_dict = {k: dict() for k in datatypes}
    climatedata = result_json['results']
    for row in climatedata:
        try:
            rowdate = datetime.datetime.strptime(row['date'], datetimefmt)
        except ValueError:
            app.logger.debug("Invalid datetime %s", row['date'])
        else:
            row_month_no = rowdate.month
            value = row['value']
            if value < 0:
                value = 0
            data_dict[row['datatype']][row_month_no] = value

    temp_risk = None
    rain_risk = None
    
    # http://www.ncbi.nlm.nih.gov/pmc/articles/PMC4001452/
    # Aedes albopictus is not expected to survive average January temperatures of -5 C (23 F)
    # Tenths of degrees Fahrenheit
    jan_temp = data_dict['MLY-TAVG-NORMAL'].get(1)
    if jan_temp is not None:
        temp_risk = bool(jan_temp * 0.1 > 23.0)

    # Aedes albopictus requires a minimum annual rainfall of ~250 mm (9.8 inches)
    # hundredths of inches
    rain_in = sum(data_dict['MLY-PRCP-NORMAL'].values())
    rain_risk = bool(rain_in * 0.01 >= 9.8)


    if temp_risk and rain_risk:
        result_dict['mosquito_risk'] = True

    if (temp_risk is not None and not temp_risk) or (rain_risk is not None and not rain_risk):
        result_dict['mosquito_risk'] = False
        result_dict['mosquito_season'] = [0] * 12
    else:
        # http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3700474/
        # roughly 100 degree days for Culex
        growing_ints = np.array([data_dict['MLY-GRDD-BASE57'].get(m + 1, 0) for m in range(12)])
        cumulative_gdd = np.cumsum(growing_ints)
        growing_bool = cumulative_gdd > 100

        # tmin 9.6 C (49.28 F)
        # tmax 37 C (98.6 F)
        tmin = 49.28
        tmax = 98.6

        # Tenths of degrees Fahrenheit
        month_temps = np.array([data_dict['MLY-TAVG-NORMAL'].get(m + 1) for m in range(12)]) * 0.1
        month_bool = (month_temps >= tmin) & (month_temps <= tmax)

        mosquito_season = growing_bool & month_bool

        result_dict['mosquito_season'] = mosquito_season

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
            row[x] = row[x].split()[0].replace(",", "")
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

def get_population(state, county=None):

    result = dict(error=None,
                  state_pop=None,
                  county_pop=None)
    state_pop = None
    county_pop = None

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
            state_pop = row[pop_index]
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
                county_pop = row[c_pop_index]
                break

    errors = list()
    # Cast populations to integer
    if state_pop is not None:
        try:
            state_pop = int(state_pop)
        except ValueError:
            errors.append("Incorrectly formatted state population")
        else:
            result['state_pop'] = state_pop
    if county_pop is not None:
        try:
            county_pop = int(county_pop)
        except ValueError:
            errors.append("Incorrectly formatted county population")
        else:
            result['county_pop'] = county_pop

    if errors:
        result['error'] = errors

    return result

if __name__ == "__main__":
    app.run()
