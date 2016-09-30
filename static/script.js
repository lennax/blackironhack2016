/**
Copyright 2016 Lenna X. Peterson
**/

// Nav tabs
$('#myNavTabs a').click(function (e) {
    "use strict";
    //console.log("click");
    e.preventDefault();
    $(this).tab('show');
});

// Client-side input validation
$(function () {
    "use strict";

    function disableSubmit() {
        // Disable submit
        $('#submit').attr("disabled", "disabled").addClass("disabled").attr("title", "Please fill out required values");
    };

    //disableSubmit();

    function checkSubmit(e) {
        var destinationLen = $('input[name="destination"]').val().length
        var dateVal = $('input[name="date"]').val()
            //        console.log(destinationLen, destinationLen > 0);
            //        console.log(dateVal);
            //        console.log(/^\d{4}-\d{2}-\d{2}$/.test(dateVal));
        if (destinationLen > 0 && /^\d{4}-\d{2}-\d{2}$/.test(dateVal)) {
            $('#submit').removeAttr("disabled").removeClass("disabled").attr("title", "Submit form")
        } else {
            disableSubmit();
        }
    }

    $('input[name="destination"]').on('keyup textinput', checkSubmit);
    $('input[name="date"]').on('change', checkSubmit);

});

// Gauge function
google.charts.load('current', {
    'packages': ['gauge']
});
//google.charts.setOnLoadCallback(drawChart);

function drawChart(risk) {
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
}

// map
var map;
$(function () {
    "use strict";

    function initMap() {

        // Geographic center of continental US
        //var location = new google.maps.LatLng(39.8282, -98.5795);

        var location = new google.maps.LatLng(40.4237, -86.9212);

        var mapCanvas = document.getElementById('map');
        var mapOptions = {
            center: location,
            zoom: 12,
            //            panControl: false,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        map = new google.maps.Map(mapCanvas, mapOptions);

    }

    google.maps.event.addDomListener(window, 'load', initMap);


});

// Geocoding promise
var geocoder = new google.maps.Geocoder();

function geocode(address) {
    "use strict";
    // Return a new promise.
    return new Promise(function (resolve, reject) {
        geocoder.geocode({
            'address': address
        }, function (results, status) {
            if (status == 'OK') {
                resolve(results[0]);
            } else {
                reject(Error(status));
            }
        });
    });
}

// Process form and call python
$(function () {
    "use strict";

    function submit_form(e) {

        var destination = $('input[name="destination"]').val();
        //console.log(destination)

        geocode(destination).then(function (response) {
            //console.log("Success!", response);
            map.fitBounds(response.geometry.viewport);
            var marker = new google.maps.Marker({
                map: map,
                position: response.geometry.location
            });
            return response;
        }, function (error) {
            alert('Geocode not successful: ' + status);
        }).then(function (response) {
            // TODO determine how to parse address_components
            var state;
            //            console.log(response.address_components);
            for (var x = 0; x < response.address_components.length; x++) {
                var component = response.address_components[x];
                //                console.log(component);
                //                console.log(component.types[0]);
                if (component.types[0] == "administrative_area_level_1") {
                    state = component.long_name
                    console.log(component.long_name)
                }

            }
            //console.log(response.address_components[2].long_name);
            $.getJSON($SCRIPT_ROOT + '/calculate', {
                    lat: response.geometry.location.lat(),
                    lng: response.geometry.location.lng(),
                    date: $('input[name="date"]').val(),
                    state: state,
                },
                function (data) {
                    if (data.result.error != 0) {
                        $('#result').text("Error: " + data.result.error);
                    } else {
                        console.log(data.result);
                        $('input[name=destination]').focus().select();
                        //alert(data.result);
                        drawChart(data.result.risk);
                        //console.log(data.result.text)
                        $('#result').text(data.result.text);
                    }
                });
        });

        return false;
    };

    $('input#submit').bind('click', submit_form);

    $('input[type=text]').bind('keydown', function (e) {
        if (e.keyCode == 13) {
            submit_form(e);
        }
    });

    $('input[name=destination]').focus();



});