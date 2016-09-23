/**
Copyright 2016 Lenna X. Peterson
**/


// Nav tabs
$('#myNavTabs a').click(function (e) {
    //console.log("click");
    e.preventDefault();
    $(this).tab('show');
});

// Date picker
$(function () {
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

function drawChart() {

    var data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
          ['Risk', 10]
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
$(function () {

    function initMap() {

        var location = new google.maps.LatLng(40.4237, -86.9212);

        var mapCanvas = document.getElementById('map');
        var mapOptions = {
            center: location,
            zoom: 12,
            //            panControl: false,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        }
        var map = new google.maps.Map(mapCanvas, mapOptions);

    }

    google.maps.event.addDomListener(window, 'load', initMap);


});

// Process form and call python
$(function () {
    var submit_form = function (e) {
        $.getJSON('http://127.0.0.1:5000/calculate', {
            destination: $('input[name="destination"]').val(),
            date: $('input[name="date"]').val()

        }, function (data) {
            console.log(data.result);
            //$('#result').text(data.result);
            $('input[name=destination]').focus().select();
            //alert(data.result);
            drawChart();
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