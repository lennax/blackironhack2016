/**
Copyright 2016 Lenna X. Peterson
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
  var destinationLen = $('input[name="destination"]').val().length;
  var dateVal = $('input[name="date"]').val();
  //        console.log(destinationLen, destinationLen > 0);
  //        console.log(dateVal);
  //        console.log(/^\d{4}-\d{2}-\d{2}$/.test(dateVal));
  return destinationLen && /^\d{4}-\d{2}-\d{2}$/.test(dateVal);
};

MyApp.initMap = function () {
  "use strict";

  // Geographic center of continental US
  //var location = new google.maps.LatLng(39.8282, -98.5795);

  // Purdue
  var location = new google.maps.LatLng(40.4237, -86.9212);

  var mapCanvas = document.getElementById('map');
  var mapOptions = {
    center: location,
    zoom: 12,
    //            panControl: false,
    mapTypeId: google.maps.MapTypeId.ROADMAP
  };
  // Not sure if this needs to be declared outside
  MyApp.map = new google.maps.Map(mapCanvas, mapOptions);

};

MyApp.drawChart = function (risk) {
  "use strict";

  var data = google.visualization.arrayToDataTable([
    ['Label', 'Value'],
    ['Risk', risk]
  ]);

  var options = {
    width: 120,
    height: 120,
    redFrom: 90,
    redTo: 100,
    yellowFrom: 75,
    yellowTo: 90,
    majorTicks: 3,
    minorTicks: 3
  };

  var chart = new google.visualization.Gauge(document.getElementById('gauge'));

  chart.draw(data, options);

  // setInterval(function () { // data.setValue(0, 1, 40 + Math.round(60 * Math.random())); // chart.draw(data, options); // }, 13000);  
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
      if (status == 'OK') {
        resolve(results[0]);
      } else {
        reject(Error(status));
      }
    });
  });
};

MyApp.submitForm = function () {
  "use strict";

  if (MyApp.validData()) {

    var destination = $('input[name="destination"]').val();
    //console.log(destination)

    MyApp.geocode(destination).then(function (response) {
      //console.log("Success!", response);
      MyApp.map.fitBounds(response.geometry.viewport);
      var marker = new google.maps.Marker({
        map: MyApp.map,
        position: response.geometry.location
      });
      return response;
    }, function (error) {
      alert('Geocode not successful: ' + status);
    }).then(function (response) {
      // TODO determine how to parse address_components
      var country, state, county, component;
      //            console.log(response.address_components);
      for (var x = 0; x < response.address_components.length; x++) {
        component = response.address_components[x];
        console.log(component);
        //                console.log(component.types[0]);
        //        switch(component.types[0]) {
        //          case "country":
        //            country = component.long_name;
        //          case "administrative_area_level_1":
        //            state = component.long_name;
        //          case "administrative_area_level_2":
        //            county = component.long_name;   
        //        };
        if (component.types[0] == "country") {
          country = component.long_name;
        } else if (component.types[0] == "administrative_area_level_1") {
          state = component.long_name;
        } else if (component.types[0] == "administrative_area_level_2") {
          county = component.long_name;
        };
        //        if (component.types[0] == "administrative_area_level_1") {
        //          state = component.long_name
        //          console.log(component.long_name)
        //        }

      }
      if (country != "United States") {
        $('#result').text("Error: data not available outside the US");
        return 1
      };
      console.log(country);
      console.log(state);
      console.log(county);
      //console.log(response.address_components[2].long_name);
      $.getJSON($SCRIPT_ROOT + '/calculate', {
          lat: response.geometry.location.lat(),
          lng: response.geometry.location.lng(),
          date: $('input[name="date"]').val(),
          state: state,
          county: county,
        },
        function (data) {
          if (data.result.error != 0) {
            $('#result').text("Error: " + data.result.error);
            return 1
          } else {
            console.log(data.result);
            $('input[name=destination]').focus().select();
            //alert(data.result);
            MyApp.drawChart(data.result.risk);
            //console.log(data.result.text)
            $('#result').text(data.result.text);
          }
        });
    });
  };

  return false;
};


// Process form and call python
$(document).ready(function () {
  "use strict";

  // Add functionality to nav tabs
  $('#myNavTabs a').click(function (e) {
    "use strict";
    //console.log("click");
    e.preventDefault();
    $(this).tab('show');
  });

  // Load Google chart package
  google.charts.load('current', {
    'packages': ['gauge']
  });

  // Load map
  google.maps.event.addDomListener(window, 'load', MyApp.initMap);

  // Client-side validation of input
  $('input[name="destination"]').on('keyup textinput', MyApp.checkSubmit);
  $('input[name="date"]').on('change', MyApp.checkSubmit);

  // Bind button click to submit
  $('input#submit').bind('click', MyApp.submitForm);

  // Bind enter to submit
  // FIXME require input validation
  $('input[type=text]').bind('keydown', function (e) {
    if (e.keyCode == 13) {
      MyApp.submitForm(e);
    }
  });

  // Put cursor into first input box
  $('input[name=destination]').focus();


});