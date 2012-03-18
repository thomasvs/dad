$(document).ready(function() {
    var API_KEY = 'N6E4NIOVYMTHNDM8J';
    var echonest = new EchoNest(API_KEY);

    document.audios = {};
    document.start = new Date().getTime();
    console.log('Document ready at ' + document.start);


    $("#clock").clock({"timestamp": new Date().getTime()});

    var ws;
    var url = 'ws' + document.URL.slice(4) + 'test';
    if (typeof MozWebSocket != "undefined") {
        ws = new MozWebSocket(url);
    } else {
        ws = new WebSocket(url);
    }
    ws.onmessage = function(evt) {
        console.log('ws: message: ' + evt.data);
        var message = jQuery.parseJSON(evt.data);
        if (message.command == 'load') {
            console.log('ws: load: id ' + message.id + ': ' + message.artists + ' - ' + message.title);
            $('#audio > tbody:last').append(
                        '<tr><td>' + message.id + '</td>' +
                    '<td>' + message.artists + '</td>' +
                    '<td>' + message.title + '</td>' +
                    '<td>' + new Date(message.when * 1000) + '</td>' +
                    '<td><audio id="' + message.id + '" src="' + message.uri + '" controls="controls"/></td></tr>');
            var audio = $('#' + message.id).get(0);
            document.audios[message.id] = audio;

            when = message.when * 1000;
            var remaining = when - new Date().getTime();
            at.at(function() {
                var a = document.audios[message.id];
                console.log('at.at: id ' + message.id + ': play after ' + (new Date().getTime() - document.start) + ' sec since document.start');

                offset = message.offset;
                console.log('at.at: id ' + message.id + ': start track at ' + offset + ' sec');
                if (remaining < 0) {
                    // FIXME: handle forwarding passed the end, which plays from 0
                    console.log('at.at: id ' + message.id + ': forward track by ' + (-remaining) + ' msec');
                    offset += -remaining / 1000.0;
                }

                // we can only seek after we have metadata
                function loadSeek(event) {
                    console.log('loadSeek: id ' + message.id + ': set currentTime to ' + offset);
                    a.currentTime = offset;
                }
                audio.addEventListener('loadedmetadata', loadSeek, false);
                a.play();

	    echonest.artist(message.artists[0]).images( function(imageCollection) {
		console.log(imageCollection);
		var images = [];
		for (i in imageCollection.data.images) {
		    images.push({
                        src: imageCollection.data.images[i].url,
                        fade: 3000
                    });
		}
                $.vegas('slideshow', {
                delay:       10000,
                backgrounds: images
                })('overlay', {
                    src: 'vegas/overlays/13.png',
                    opacity: 0.5
                });

	    });

            }, when);
            console.log('load: id ' + message.id + ': scheduled play at ' + when + ' epoch sec in ' + remaining + ' msec');
        }
        if (message.command == 'play') {
                console.log('Schedule play of ' + message.id +
                        ' at' + (message.when * 1000) + ' sec');
            at.at(function() {
                a = document.audios[message.id];
                    console.log('Play ' + a + (new Date().getTime() - document.start));
                a.play();

            }, message.when * 1000);
        }
    };

    ws.onopen = function(evt) {
        $('#conn_status').html('<b>Connected</b>');
        ws.send('Test data');
    };

    ws.onerror = function(evt) {
        $('#conn_status').html('<b>Error</b>');
    };

    ws.onclose = function(evt) {
        $('#conn_status').html('<b>Closed</b>');
    };

});
