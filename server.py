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

    errors = list()

    # parse date
    datefmt = "%Y-%m-%d"
    try:
        parsed_date = datetime.datetime.strptime(mydate, datefmt)
    except ValueError:
        # Server-side input validation
        errors.append('invalid date format')

    if not state:
        errors.append('state not specified')

    if errors:
        msg = ", ".join(errors)
        return jsonify(result=dict(error=msg))

#    print destination
    kwargs = dict(lat=lat,
                  lng=lng,
                  mydate=parsed_date,
                  state=state,
                  county=county)
    return jsonify(result=get_result(**kwargs))

def get_result(lat, lng, mydate, state, county=None):

    result_dict = dict(text=None,
                       destrisk=None,
                       inrisk=None,
                       error=0)
  
    latlng = (lat, lng)
    #print latlng
    app.logger.debug(latlng)

    # Risk factors:
        # How many people are infected in the state?
        # How populous is the destination?
        # Are mosquitoes active in the destination?
            # Is it mosquito season?

    errors = dict(cases=None,
                  pop=None,
                  climate=None)

    risks = dict(cases=None,
                 state_pop=None,
                 county_pop=None,
                 mosquito_risk=None,
                 mosquito_season=None)

    indiana_risks = dict(cases=None,
                         state_pop=None,
                         county_pop=None,
                         mosquito_risk=None,
                         mosquito_season=None)

    # How many people are infected in the state?
    app.logger.debug(state)
    cases = None
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
            #cases = row[1] + row[2]
        if row[0].lower() == "indiana":
            indiana_risks['cases'] = add_zika_row(row)
            #indiana_risks['cases'] = row[1] + row[2]
    if cases is None:
        errors['cases'] = "No case data was found for %s." % state
    else:
        risks['cases'] = cases

    # How populous is the destination?
    pop_dict = get_population(state=state, county=county)
    if not pop_dict.pop('error'):
        risks.update(pop_dict)
    else:
        pop_err = "No population data was found for %s." % state
        if county is not None:
            pop_err += " county %s" % county
        errors['pop'] = pop_err

    in_pop_dict = get_population(state="indiana", county="tippecanoe")
    if not in_pop_dict.pop('error'):
        indiana_risks.update(in_pop_dict)

    # Are mosquitoes active in the destination?
        # Is it mosquito season?
    climate_dict = get_climate(latlng=latlng,
                               mydate=mydate)
    if climate_dict['error']:
        errors['climate'] = climate_dict.pop('error')
    else:
        risks.update(climate_dict)

    in_climate_dict = get_climate_for_station(stationid="USW00014835",
                                              mydate=mydate)
    if not in_climate_dict['error']:
        indiana_risks.update(in_climate_dict)

    result_text = """
   <table class="tg">
     <tr>
       <th>Risk Factor<br></th>
       <th>{inloc}<br></th>
       <th>{destination}<br></th>
     </tr>
     <tr>
       <td>Cases statewide</td>
       <td class="{incasesclass}">{incases}<br></td>
       <td class="{casesclass}">{cases}</td>
     </tr>
     <tr>
       <td>Population</td>
       <td class="{inpopclass}">{inpop}</td>
       <td class="{popclass}">{pop}</td>
     </tr>
     <tr>
       <td>Mosquitoes</td>
       <td class="{inclimateclass}">{inclimate}</td>
       <td class="{climateclass}">{climate}</td>
     </tr>
   </table>
   <ul>
   <li>{casesummary}</li>
   <li>{popsummary}</li>
   <li>{climatesummary}</li>
   </ul>
   Overall, the risk of getting Zika virus in the USA is low. For context, the following chart shows the rate of cases of Zika virus in Indiana and {state} compared to the annual risk of selected causes of death.
     """
    #"""
    #{destination} has {pop} people.
    #The state of {dest_state} has {cases} reported cases of Zika virus.
    #{mosquito_phrase}
    #Compared to Indiana, your destination {cases_cmp}.
    #{case_vs_pop_prep}, {pop_cmp}.
    #{mosquito_cmp_phrase}
    #"""

    app.logger.debug(risks)

    result_kwargs = dict(state=state)

    # Initialize classes to "unknown"
    for datatype in "cases", "pop", "climate":
        for prefix in "", "in":
            result_kwargs['{0}{1}class'.format(prefix, datatype)] = "unknown"

    month_name = mydate.strftime("%B")

    inloc = "Indiana"
    destination = state
    pop = risks['state_pop']
    inpop = indiana_risks['state_pop']
    if county:
        inloc = "Tippecanoe County, Indiana"
        destination = "{0}, {1}".format(county, state)
        pop = risks['county_pop']
        inpop = indiana_risks['county_pop']
    result_kwargs['inloc'] = inloc
    result_kwargs['destination'] = destination

    popsummary = "No population comparison was available. In general, traveling to a less populous area may reduce your risk."
    if pop is not None and inpop is not None:
        popratio = pop * 1.0 / inpop
        if popratio > 2:
            inpopclass = "better"
            popclass = "worse"
            popsummary = "{destination} is more populous than {inloc}. You could reduce your risk by traveling to a less populous area."
        elif popratio < 0.5:
            inpopclass = "worse"
            popclass = "better"
            popsummary = "{destination} is less populous than {inloc}. This may reduce your risk."
        else:
            inpopclass = "same"
            popclass = "same"
            popsummary = "{destination} and {inloc} have similar populations. You could reduce your risk by traveling to a less populous area."
        result_kwargs['inpopclass'] = inpopclass
        result_kwargs['popclass'] = popclass
    result_kwargs['pop'] = "{0:,}".format(pop) if pop is not None else "-"
    result_kwargs['inpop'] = "{0:,}".format(inpop) if inpop is not None else "-"
    result_kwargs['popsummary'] = popsummary.format(**result_kwargs)

    incases = indiana_risks['cases']
    cases = risks['cases']
    casesummary = "No case comparison was available. In general, traveling to an area with fewer cases may reduce your risk."
    if cases is not None and incases is not None:
        caseratio = cases * 1.0 / incases
        if caseratio > 2:
            incaseclass = "better"
            caseclass = "worse"
            casesummary = "{state} has more cases of Zika virus than Indiana. You could reduce your risk by traveling to an area with fewer cases."
        elif caseratio < 0.5:
            incaseclass = "worse"
            caseclass = "better"
            casesummary = "{state} has fewer cases of Zika virus than Indiana. This may reduce your risk."
        else:
            incaseclass = "same"
            caseclass = "same"
            casesummary = "{state} and Indiana have similar numbers of Zika virus cases. You could reduce your risk by traveling to an area with fewer cases."
        result_kwargs['incasesclass'] = incaseclass
        result_kwargs['casesclass'] = caseclass
    result_kwargs['cases'] = "{0:,}".format(cases) if cases is not None else "-"
    result_kwargs['incases'] = "{0:,}".format(incases) if incases is not None else "-"
    result_kwargs['casesummary'] = casesummary.format(state=state)

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

    mosquito_risk_names = ["Minimal", "Unknown", "Out of season", "In season"]
    mosquito_risk_classes = ["better", "unknown", "better", "worse"]
    def parse_risk(mosquito_risk, mosquito_season, **kwargs):
        if mosquito_risk is None or mosquito_risk:
            if mosquito_season is None:
                # If mosquito season is unknown, overall risk is unknown
                return 1
            elif mosquito_season:
                # Mosquito season is risk
                return 3
            else:
                # Not mosquito season reduces risk
                return 2
        else:
            # No mosquito risk
            return 0

    in_mosquito_risk = parse_risk(**indiana_risks)
    result_kwargs['inclimate'] = mosquito_risk_names[in_mosquito_risk]
    result_kwargs['inclimateclass'] = mosquito_risk_classes[in_mosquito_risk]
    mosquito_risk = parse_risk(**risks)
    result_kwargs['climate'] = mosquito_risk_names[mosquito_risk]
    result_kwargs['climateclass'] = mosquito_risk_classes[mosquito_risk]

    climate_summary = list()
    if mosquito_risk_names[in_mosquito_risk] == "In season":
        climate_summary.append("{month_name} is mosquito season in West Lafayette, Indiana. You could reduce your risk by leaving Indiana for an area without mosquitoes.")
    if mosquito_risk_names[mosquito_risk] == "In season":
        climate_summary.append("{month_name} is mosquito season in {destination}. You could reduce your risk by traveling before or after mosquito season or to a different area without mosquitoes.")
    if not climate_summary:
        climate_sentence = "{month_name} is not mosquito season for either West Lafayette, Indiana or {state}, so the risk of getting infected by a mosquito is low."
    else:
        climate_sentence = " ".join(climate_summary)
    result_kwargs['climatesummary'] = climate_sentence.format(month_name=month_name, **result_kwargs)

    #if errors['cases']:
        #case_text = errors['cases']
    #else:
        #case_text = "{0} has {1} reported cases of Zika virus".format(state, risks['cases'])
    #result_text.append(case_text)

    #result_kwargs = dict(dest_state=state)
    #destination = state
    #pop = risks['pop']['state_pop']
    #if county:
        #destination = "{0}, {1}".format(county, state)
        #pop = risks['pop']['county_pop']
    #result_kwargs['destination'] = destination
    #result_kwargs['pop'] = pop

    # Needed results:
        # Text summary
        # destination cases per 1M
        # Indiana cases per 1M

    ## TODO handle missing data classes better
    #if state is not None and cases is not None:
        #result_text += " {0} total cases of Zika have been reported in {1}.".format(cases, state)
        ## TODO logistic function
        #risk = min(100, risk * 2)

    #if pop_sentence is not None:
        #result_text = result_text + " " + pop_sentence

    result_dict['text'] = result_text.format(**result_kwargs)
    result_dict['destrisk'] = rate_per_mil(**risks)
    result_dict['inrisk'] = rate_per_mil(**indiana_risks)

    return result_dict

def rate_per_mil(cases, state_pop, **kwargs):
    if cases is not None and state_pop:
        # Pseudocount
        if cases == 0:
            cases = 1
        rate = cases * 1.0 / state_pop
        rate_per_m = rate * 1000000
        return rate_per_m

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

def get_climate(latlng, mydate):

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
    ftp.quit()
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

    # TODO check that the smallest distance is small

    #print stationid
    app.logger.debug(stationid)

    return get_climate_for_station(stationid=stationid, mydate=mydate)

def get_climate_for_station(stationid, mydate):

    # Are mosquitoes active in the destination?
    # Is it mosquito season?
    result_dict = dict(mosquito_risk=None,
                       mosquito_season=None,
                       error="")

    month_number = mydate.month

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

    ftp = FTP(open_climate_ftp)
    ftp.login()
    ftp.cwd("/pub/data/normals/1981-2010/")

    def get_row(filename):
        row_list = list()
        ftp.retrlines("RETR {0}".format(filename), row_list.append)
        for line in row_list:
            stnid = line[:11]
            if stnid == stationid:
                return line

    #ftp.retrlines("RETR products/auxiliary/station/{0}-normals.txt".format(stationid))

    ##### Are mosquitoes active in the destination?
    
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

    if temp_risk is not None and not temp_risk and rain_risk is not None and not rain_risk:
        result_dict['mosquito_risk'] = False

    # Is it mosquito season?
    else:
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

        #cooling_text = "mosquitoes have likely not yet hatched"
        mosquito_season = False
        if cooling_value > 100:
            #cooling_text = "mosquitoes have likely hatched"

            # tmin 9.6 C (49.28 F)
            # tmax 37 C (98.6 F)
            # TODO convert to quadratic
            month_temp = tavg_ints[month_number - 1]

            #conjunction = "but"
            #risk = 1
            tmin = 49.28
            tmax = 98.6
            if month_temp >= tmin and month_temp <= tmax:
                mosquito_season = True
            #if month_temp < tmin:
                #temp_text = "it is too cold for mosquitoes"
            #elif month_temp > tmax:
                #temp_text = "it is too hot for mosquitoes"
            #else:
                #conjunction = "and"
                #temp_text = "it is the right temperature for mosquitoes"
                #risk = 15

            #cooling_text = " ".join([cooling_text, conjunction, temp_text])

        result_dict['mosquito_season'] = mosquito_season

        # Aedes aegypti populations are not necessarily rainfall dependent
        #    hundredths of inches for average monthly/seasonal/annual precipitation,
        #    month-to-date/year-to-date precipitation, and percentiles of precipitation.
        #    e.g., "1" is 0.01" and "1486" is 14.86"
        #        precip_result = get_row("products/precipitation/mly-prcp-normal.txt")
        #    #    print precip_result
        #        precip_list = precip_result.split()
        #        precip_value = int(precip_list[month_number][:-1]) * 0.01

        #result_text = "The climate at your destination is hospitable to mosquitoes. In {month_name}, {cooling_text}.".format(
            #cooling_text=cooling_text, month_name=month_name)

        # TODO compute some sort of risk
        #risk = 15

    #else:
        #result_text = "The climate at your destination is not hospitable to mosquitoes."
        #risk = 1

    ftp.quit()

    #result_dict['text'] = result_text
    #result_dict['risk'] = risk
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
            result['state_pop'] = row[pop_index]
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
                break

    errors = list()
    # Cast populations to integer
    if result['state_pop'] is not None:
        try:
            result['state_pop'] = int(result['state_pop'])
        except ValueError:
            errors.append("Incorrectly formatted state population")
    if result['county_pop'] is not None:
        try:
            result['county_pop'] = int(result['county_pop'])
        except ValueError:
            errors.append("Incorrectly formatted county population")

    if errors:
        result['error'] = errors

    return result

if __name__ == "__main__":
    app.run()
