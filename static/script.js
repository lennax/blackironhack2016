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

// Date picker
$(function () {
    "use strict";
    $("#datepicker").datepicker({
        minDate: 0,
        changeMonth: true,
        changeYear: true
    });
    $("#anim").on("change", function () {
        $("#datepicker").datepicker("option", "showAnim", $(this).val());
    });
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
        var location = new google.maps.LatLng(39.8282, -98.5795);

        var mapCanvas = document.getElementById('map');
        var mapOptions = {
            center: location,
            zoom: 3,
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

    var submit_form = function (e) {

        // TODO do light client side input validation
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
            console.log(response.address_components);
            $.getJSON('http://127.0.0.1:5000/calculate', {
                    lat: response.geometry.location.lat(),
                    lng: response.geometry.location.lng(),
                    date: $('input[name="date"]').val()
                },
                function (data) {
                    console.log(data.result);
                    //$('#result').text(data.result);
                    $('input[name=destination]').focus().select();
                    //alert(data.result);
                    drawChart(data.result.risk);
                    //console.log(data.result.text)
                    // TODO fix behavior on second search
                    $('input#submit').parent().after("<p>" + data.result.text + "</p>");
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