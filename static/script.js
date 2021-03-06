/**
Copyright 2016 Lenna X. Peterson
This file is part of Travel Risk Evaluation.
 **/

if (typeof MYAPPLICATION === "undefined") {
  var MyApp = {};
}

MyApp.disableSubmit = function () {
  "use strict";
  $('#submit').attr("disabled", "disabled").addClass("disabled").attr("title", "Please fill out required values");
};

// Client-side input validation
MyApp.checkSubmit = function (e) {
  "use strict";
  if (MyApp.validData()) {
    $('#submit').removeAttr("disabled").removeClass("disabled").attr("title", "Submit form");
  } else {
    MyApp.disableSubmit();
  }
};

MyApp.validData = function () {
  "use strict";
  var destinationLen = $('input[name="destination"]').val().length,
    dateVal = $('select[name="date"]').val();
  return destinationLen && dateVal >= 0 && dateVal <= 11;
};

MyApp.initMap = function () {
  "use strict";

  var location, mapCanvas, mapOptions, map, input, autocomplete, infowindow, marker;

  // Geographic center of continental US
  //var location = new google.maps.LatLng(39.8282, -98.5795);

  // Purdue
  location = new google.maps.LatLng(40.4237, -86.9212);

  mapCanvas = document.getElementById('map');
  mapOptions = {
    center: location,
    zoom: 12,
    //            panControl: false,
    mapTypeId: google.maps.MapTypeId.ROADMAP
  };
  MyApp.map = new google.maps.Map(mapCanvas, mapOptions);

  input = document.getElementById('destination');

  //map.controls[google.maps.ControlPosition.TOP_LEFT].push(input);

  autocomplete = new google.maps.places.Autocomplete(input);
  autocomplete.bindTo('bounds', MyApp.map);

  MyApp.infowindow = new google.maps.InfoWindow();
  MyApp.marker = new google.maps.Marker({
    map: MyApp.map,
    anchorPoint: new google.maps.Point(0, -29)
  });

  autocomplete.addListener('place_changed', function () {
    var place = autocomplete.getPlace();
    MyApp.updateMap(place);
  });

  // Default data
  //  document.getElementById('date').valueAsDate = new Date();
  document.getElementById('date').options.selectedIndex = new Date().getMonth();
  document.getElementById('destination').value = "Miami, FL";
  MyApp.checkSubmit();
  MyApp.submitForm();
};

MyApp.updateMap = function (place) {
  "use strict";

  var placeName, address = '';

  MyApp.infowindow.close();
  MyApp.marker.setVisible(false);
  if (!place.geometry) {
    //      window.alert("Autocomplete's returned place contains no geometry");
    return;
  }

  // If the place has a geometry, then present it on a map.
  if (place.geometry.viewport) {
    MyApp.map.fitBounds(place.geometry.viewport);
  } else {
    MyApp.map.setCenter(place.geometry.location);
    MyApp.map.setZoom(17);
  }

  MyApp.marker.setPosition(place.geometry.location);
  MyApp.marker.setVisible(true);

  if (place.address_components) {
    address = [
      ((place.address_components[0] && place.address_components[0].short_name) || ''),
      ((place.address_components[1] && place.address_components[1].short_name) || ''),
      ((place.address_components[2] && place.address_components[2].short_name) || '')
    ].join(' ');
  }

  if (typeof place.name !== 'undefined') {
    placeName = place.name;
  } else {
    placeName = ((place.address_components[0] && place.address_components[0].short_name) || '');
  }

  MyApp.infowindow.setContent('<div><strong>' + placeName + '</strong><br>' + address);
  MyApp.infowindow.open(MyApp.map, MyApp.marker);
};

MyApp.drawGauge = function (risk) {
  "use strict";

  var data, options, chart;

  // Load Google chart package
  google.charts.load('current', {
    'packages': ['gauge']
  });

  data = google.visualization.arrayToDataTable([
    ['Label', 'Value'],
    ['Risk', risk]
  ]);

  options = {
    width: 120,
    height: 120,
    redFrom: 90,
    redTo: 100,
    yellowFrom: 75,
    yellowTo: 90,
    majorTicks: 3,
    minorTicks: 3
  };

  chart = new google.visualization.Gauge(document.getElementById('gauge'));

  chart.draw(data, options);

  // setInterval(function () { // data.setValue(0, 1, 40 + Math.round(60 * Math.random())); // chart.draw(data, options); // }, 13000);  
};

MyApp.commaFormat = Plotly.d3.format(',d');

MyApp.drawBar = function (div, x_arr, ylabel) {
  "use strict";
  Plotly.newPlot(div, [{
    type: 'bar',
    x: x_arr,
    y: new Array(x_arr.length).fill(0),
    name: ylabel,
    mode: 'legendonly',
    showlegend: false
  }], {
    title: ylabel,
    xaxis: {
      fixedrange: true
    },
    yaxis: {
      //      title: ylabel,
      fixedrange: true,
      rangemode: 'nonnegative'
    },
    barmode: 'stack',
    showlegend: 'false',
    width: 275,
    height: 350,
    margin: {
      l: 50,
      r: 50,
      b: 50,
      t: 50,
      pad: 4
    },
    paper_bgcolor: 'rgb(254, 247, 234)',
    plot_bgcolor: 'rgb(254, 247, 234)'
  });
};

MyApp.updateBar = function (div, x_arr, y_arr, color) {
  "use strict";
  var annotations,
    i;
  Plotly.deleteTraces(div, 0);
  Plotly.addTraces(div, {
    type: 'bar',
    x: x_arr,
    y: y_arr,
    marker: {
      color: color
    },
    showlegend: false,
    hoverinfo: 'none'
  });
  annotations = [];
  for (i = 0; i < x_arr.length; i += 1) {
    annotations.push({
      x: x_arr[i],
      y: y_arr[i],
      text: MyApp.commaFormat(y_arr[i]),
      xanchor: 'center',
      yanchor: 'bottom',
      showarrow: false
    });
  }
  Plotly.relayout(div, {
    annotations: annotations
  });
};

MyApp.drawLadder = function (div) {
  "use strict";

  var cause, rate, breakpoint, deathColor, deathMarker, dummytrace, smalltrace, largetrace, data, xticktext, xtickvals, layout;

  cause = [
    'Heart disease',
    'Lung cancer',
    'Car crash',
    'Firearm homicide',
    'Plane crash',
    'Drowning in bathtub',
    'Arthropod-borne virus',
    'Lightning'
  ];

  rate = [
    1440.6,
    524.8,
    140.3,
    38.8,
    2,
    1.3,
    0.3,
    0.10
  ];

  breakpoint = 4;

  deathColor = 'rgba(119, 190, 222, 0.95)';
  deathMarker = {
    color: deathColor,
    line: {
      color: deathColor,
      width: 1
    },
    symbol: 'circle',
    size: 16
  };

  dummytrace = {
    type: 'scatter',
    x: [0],
    y: [0],
    mode: 'markers',
    name: 'Deaths per 1M in USA',
    marker: deathMarker
  };

  smalltrace = {
    type: 'scatter',
    x: rate.slice(breakpoint, rate.length),
    y: rate.slice(breakpoint, rate.length),
    mode: 'markers+text',
    text: cause.slice(breakpoint, cause.length),
    textposition: 'right',
    name: 'Deaths per 1M',
    showlegend: false,
    marker: deathMarker
  };

  largetrace = {
    type: 'scatter',
    x: rate.slice(0, breakpoint),
    y: rate.slice(0, breakpoint),
    mode: 'markers+text',
    text: cause.slice(0, breakpoint),
    textposition: 'left',
    name: 'Deaths per 1M in USA',
    showlegend: false,
    marker: deathMarker
  };

  //  var gbsCases = 15;
  //  var gbstrace = {
  //    type: 'scatter',
  //    x: [gbsCases],
  //    y: [gbsCases],
  //    //y: ['Guillain-Barré Syndrome'],
  //    text: ['Guillain-Barré Syndrome'],
  //    textposition: 'center',
  //    mode: 'markers',
  //    name: 'Cases per 1M in USA',
  //    //showlegend: false,
  //    marker: caseMarker
  //  };

  data = [smalltrace, largetrace,
//              gbstrace,
              dummytrace];

  xtickvals = [0.1, 1, 10, 100, 1000];
  xticktext = ["1 in 10 million", "1 in 1 million", "1 in 100,000", "1 in 10,000", "1 in 1,000"];

  layout = {
    title: 'Comparison of risks',
    xaxis: {
      showgrid: true,
      showline: true,
      fixedrange: true,
      linecolor: 'rgb(102, 102, 102)',
      titlefont: {
        font: {
          color: 'rgb(204, 204, 204)'
        }
      },
      tickfont: {
        font: {
          color: 'rgb(102, 102, 102)'
        }
      },
      type: 'log',
      rangemode: 'nonnegative',
      tickvals: xtickvals,
      ticktext: xticktext,
      //tickmode: 'array',  // setting tickmode 'array' ignored xtickvals
      ticks: 'outside',
      tickcolor: 'rgb(102, 102, 102)'
    },
    yaxis: {
      autorange: 'reversed',
      fixedrange: true,
      showgrid: false,
      showline: false,
      zeroline: false,
      showticklabels: false,
      ticks: '',
      type: 'log',
      rangemode: 'nonnegative'
    },
    margin: {
      l: 50,
      r: 50,
      b: 50,
      t: 50,
      pad: 4
    },
    showlegend: false,
    legend: {
      orientation: 'h'
    },

    width: 550,
    height: 400,
    paper_bgcolor: 'rgb(254, 247, 234)',
    plot_bgcolor: 'rgb(254, 247, 234)'
      //  hovermode: 'closest'
  };

  Plotly.newPlot(div, data, layout);
};

MyApp.updateLadder = function (div, destcases, incases) {
  "use strict";

  var caseColor, caseMarker, caseColorIn, caseMarkerIn, zikatrace, zikatrace_in, nTraces, annotations;

  caseColor = 'rgba(211, 115, 38, 0.95)';
  caseMarker = {
    color: caseColor,
    line: {
      color: caseColor,
      width: 1
    },
    symbol: 'square',
    size: 16
  };

  caseColorIn = 'rgba(229, 170, 38, 0.95)';
  caseMarkerIn = {
    color: caseColorIn,
    line: {
      color: caseColorIn,
      width: 1
    },
    symbol: 'diamond',
    size: 16
  };

  zikatrace = {
    type: 'scatter',
    x: [destcases],
    y: [destcases],
    text: ['Zika Virus'],
    textposition: 'center',
    mode: 'markers',
    name: 'Cases per 1M in state',
    //showlegend: false,
    marker: caseMarker
  };

  zikatrace_in = {
    type: 'scatter',
    x: [incases],
    y: [incases],
    text: ['Zika Virus (IN)'],
    textposition: 'center',
    mode: 'markers',
    name: 'Cases per 1M (IN)',
    //showlegend: false,
    marker: caseMarkerIn
  };

  annotations = [
    {
      x: Math.log10(incases),
      y: Math.log10(incases),
      xref: 'x',
      yref: 'y',
      text: 'Zika Virus Syndrome (IN)',
      //        font: {
      //          color: caseColor,
      //        },
      bgcolor: 'rgba(255, 255, 255, 0.8)',
      bordercolor: caseColorIn,
      borderwidth: 2,
      showarrow: true,
      arrowwidth: 2,
      arrowcolor: 'rgb(67, 67, 67)',
      arrowhead: 2,
      ax: 100,
      ay: -10
    },
    {
      x: Math.log10(destcases),
      y: Math.log10(destcases),
      xref: 'x',
      yref: 'y',
      text: 'Zika Virus Syndrome',
      //        font: {
      //          color: caseColor,
      //        },
      bgcolor: 'rgba(255, 255, 255, 0.8)',
      bordercolor: caseColor,
      borderwidth: 2,
      showarrow: true,
      arrowwidth: 2,
      arrowcolor: 'rgb(67, 67, 67)',
      arrowhead: 2,
      ax: 100,
      ay: -10
    }
  ]

  nTraces = document.getElementById(div).data.length
  if (nTraces <= 3) {
    Plotly.addTraces(div, [zikatrace_in, zikatrace]);
  } else {
    Plotly.deleteTraces(div, 4);
    Plotly.addTraces(div, [zikatrace]);
  }

  Plotly.relayout(div, {
    annotations: annotations
  });
};

MyApp.setUpTangle = function (divId) {
  "use strict";

  var element, months, tangle;

  element = document.getElementById(divId);

  months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
  ];

  Tangle.formats.month = function (value) {
    return months[value];
  };

  MyApp.tangle = new Tangle(element, {
    initialize: function () {
      this.riskArr = null;
      this.inriskArr = null;
      this.month = new Date().getMonth();
    },
    update: function () {
      if (this.riskArr !== null && this.riskArr !== 'undefined') {
        this.risk = this.riskArr[this.month];
      }
      if (this.inriskArr !== null && this.inriskArr !== 'undefined') {
        this.inrisk = this.inriskArr[this.month];
      }

      if (this.risk && this.inrisk) {
        this.riskcmp = 0;
      } else if (!this.risk && !this.inrisk) {
        this.riskcmp = 3;
      } else if (!this.risk && this.inrisk) {
        this.riskcmp = 1;
      } else {
        this.riskcmp = 2;
      }
    }
  });
};

MyApp.updateTangle = function (risks, inrisks, month) {
  "use strict";
  MyApp.tangle.setValues({
    riskArr: risks,
    inriskArr: inrisks,
    month: month
  });
};

MyApp.geocoder = new google.maps.Geocoder();

// Geocoding promise
MyApp.geocode = function (address) {
  "use strict";
  // Return a new promise.
  return new Promise(function (resolve, reject) {
    MyApp.geocoder.geocode({
      'address': address
    }, function (results, status) {
      if (status === 'OK') {
        resolve(results[0]);
      } else {
        reject(new Error(status));
      }
    });
  });
};

MyApp.submitForm = function () {
  "use strict";

  var destination, dateInput;

  if (MyApp.validData()) {

    // Clear result divs
    $('.addtext').text('');
    $('.togglehidden').addClass('hidden');

    destination = $('input[name="destination"]').val();
    //console.log(destination)

    dateInput = parseInt($('select[name="date"]').val());
    //console.log(dateInput);

    MyApp.geocode(destination).then(function (response) {
      //console.log("Success!", response);
      MyApp.updateMap(response);
      return response;
    }, function (error) {
      alert('Geocode not successful: ' + status);
    }).then(function (response) {
      // TODO determine how to parse address_components
      var x, country, state, stateAbbr, county, component,
          deststatepop, instatepop, destcases, incases;
      //            console.log(response.address_components);
      for (x = 0; x < response.address_components.length; x += 1) {
        component = response.address_components[x];
        //        console.log(component);
        if (component.types[0] === "country") {
          country = component.long_name;
        } else if (component.types[0] === "administrative_area_level_1") {
          state = component.long_name;
          stateAbbr = component.short_name;
        } else if (component.types[0] === "administrative_area_level_2") {
          county = component.long_name;
        }

      }
      if (country !== "United States") {
        $('#result').text("Error: data not available outside the US");
        return 1;
      }

      $('.deststate').text(state);
      $('.casesrc').hover(function () {
        $('#casebox').removeClass('inactive').addClass('highlight');
      }, function () {
        $('#casebox').addClass('inactive').removeClass('highlight');
      });
      $('.popsrc').hover(function () {
        $('#popbox').removeClass('inactive').addClass('highlight');
      }, function () {
        $('#popbox').addClass('inactive').removeClass('highlight');
      });

      //      console.log(country);
      //      console.log(state);
      //      console.log(county);
      
      $.when(
        $.ajax({
          url: $SCRIPT_ROOT + '/get_pop',
          dataType: 'json',
          data: {state: state, county: county},
          success: function (data) {
            // Display population
            var pop_x, pop_y, popColor;
            if (data.result.error) {
              $('#popsummary').text("Error: " + data.result.error);
              return 1;
            } else {
              popColor = 'rgb(119, 190, 222)';
              instatepop = data.result.instatepop;
              deststatepop = data.result.deststatepop;
              if (county !== null && county !== 'undefined') {
                pop_x = ['Tippecanoe', county.replace('County', '')];
                pop_y = [data.result.incountypop, data.result.destcountypop];
              } else {
                pop_x = ['IN', stateAbbr];
                pop_y = [instatepop, deststatepop];
              }
              MyApp.updateBar('popbox',
                pop_x, pop_y, popColor);          
              $('#popsummary').text(data.result.popsummary);
            }
          },
          error: function(XMLHttpRequest, textStatus, errorThrown) {
            $('#popsummary').text("Server error, please try again later.");
          },
          timeout: 10000
        }),
        $.ajax({
          url: $SCRIPT_ROOT + '/get_cases',
          dataType: 'json',
          data: {state: state},
          success: function (data) {
            // Display cases
            var caseColor;
            if (data.result.error) {
              $('#casesummary').text("Error: " + data.result.error);
              return 1;
            } else {
              caseColor = 'rgb(229, 170, 38)';
              incases = data.result.incases;
              destcases = data.result.destcases;
              // update case and pop charts
              MyApp.updateBar('casebox',
                ['IN', stateAbbr], [incases, destcases], caseColor);
              $('#casesummary').text(data.result.casesummary);
            }
          },
          error: function(XMLHttpRequest, textStatus, errorThrown) {
            $('#casesummary').text("Server error, please try again later.");
          },
          timeout: 10000
        })
      ).then(function () {
        // Display risk rate
        var destrisk, inrisk;
        if (deststatepop && destcases) {
          console.log(deststatepop);
          console.log(destcases);
          destrisk = destcases / deststatepop * 1000000;
        } else {
          destrisk = 0;
        }
        if (instatepop && incases) {
          inrisk = incases / instatepop * 1000000;
        } else {
          inrisk = 0;
        }
        MyApp.updateLadder('ladder', destrisk, inrisk);
      }, function () {
        // Risk fail
      });
      
      $.ajax({
        url: $SCRIPT_ROOT + '/get_climate',
        dataType: 'json',
        data: {
          lat: response.geometry.location.lat(),
          lng: response.geometry.location.lng(),
          date: dateInput
        },
        success: function (data) {
          // Display climate
          if (data.result.error) {
            $('#climateerror').text("Error: " + data.result.error);
            return 1;
          } else {
            $('#climatesummary').removeClass('hidden');
            if (data.result.destclimaterisk === 0) {
              $('#climatefalse').removeClass('hidden');
            } else if (data.result.destclimaterisk === 1) {
              $('#climateunknown').removeClass('hidden');
            }
            console.log(data.result.destclimate_arr);
            console.log(data.result.inclimate_arr);
            MyApp.updateTangle(data.result.destclimate_arr,
              data.result.inclimate_arr,
              dateInput);
          }
        },
          error: function(XMLHttpRequest, textStatus, errorThrown) {
            $('#climateerror').text("Server error, please try again later.");
          },
        timeout: 10000
      });
    });
  }

  return false;
};

// Process form and call python
$(document).ready(function () {
  "use strict";

  var today = new Date();

  // Add functionality to nav tabs
  $('#myNavTabs a').click(function (e) {
    //console.log("click");
    e.preventDefault();
    $(this).tab('show');
  });

  // Add date
  $('.today').text(today.toLocaleDateString());

  // Load map
  google.maps.event.addDomListener(window, 'load', MyApp.initMap);

  // Init bar charts
  MyApp.drawBar('casebox', ['IN', ''], 'Cases in state');
  MyApp.drawBar('popbox', ['Tippecanoe', ''], 'Population');

  // Load ladder
  MyApp.drawLadder('ladder');

  // Set up Tangle
  MyApp.setUpTangle("climatesummary");

  // Client-side validation of input
  $('input[name="destination"]').on('keyup textinput', MyApp.checkSubmit);

  // Bind button click to submit
  $('input#submit').bind('click', MyApp.submitForm);

  // Loading animation code
  $(document).ajaxStart(function () {
    MyApp.disableSubmit();
    $('body').addClass("loading");
    console.log( "Triggered ajaxStart handler." );
  });
  $(document).ajaxStop(function () {
    $('body').removeClass("loading");
    MyApp.checkSubmit();
    console.log( "Triggered ajaxStop handler." );
  });

  // Bind enter to submit
  $('input[type=text]').bind('keydown', function (e) {
    if (e.keyCode === 13) {
      MyApp.submitForm(e);
    }
  });

  // Put cursor into first input box
  //$('input[name=destination]').focus();


<<<<<<< HEAD
});
=======
});
>>>>>>> FETCH_HEAD
