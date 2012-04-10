$(document).ready(function() {
    var API_KEY = 'N6E4NIOVYMTHNDM8J';
    var echonest = new EchoNest(API_KEY);

    var playingId = 0;
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
            // load a new track
            console.log('ws: load: id ' + message.id + ': ' + message.artists + ' - ' + message.title);

            // remove a previous one with the same id
            $('#tr-' + message.id).remove();
            if (message.id in document.audios) {
                console.log('deleting previous audio for id ' + message.id);
                delete document.audios[message.id];
            }

            // add the new one
            $('#audio > tbody:last').append(
                        '<tr id="tr-' + message.id + '"><td>' + message.id + '</td>' +
                    '<td>' + message.artists + '</td>' +
                    '<td>' + message.title + '</td>' +
                    '<td>' + new Date(message.when * 1000) + '</td>' +
                    '<td><audio id="audio-' + message.id + '" src="' + message.uri + '" controls="controls"/></td></tr>');
            var audio = $('#audio-' + message.id).get(0);
            document.audios[message.id] = audio;

            // clean up when playback ends
            $('#audio-' + message.id).bind('ended', function()  {
                console.log('ended: id ' + message.id);
                $('#tr-' + message.id).remove();
                delete document.audios[message.id];
            });

            whenMs = message.when * 1000;
            var remainingMs = whenMs - new Date().getTime();

            // play the track at the scheduled time
            at.at(function() {
                // fixme: how to unschedule ?
                if (message.id > playingId) {
                    playingId = message.id;
                }
                var a = document.audios[message.id];
                console.log('at.at: id ' + message.id + ': play after ' + (new Date().getTime() - document.start) + ' sec since document.start');

                offsetS = message.offset;
                console.log('at.at: id ' + message.id + ': start track at ' + offsetS + ' sec');
                if (remainingMs < 0) {
                    // FIXME: handle forwarding passed the end, which plays from 0
                    console.log('at.at: id ' + message.id + ': forward track by ' + (-remainingMs) + ' msec');
                    offsetS += -remainingMs / 1000.0;
                }

                // we can only seek after we have metadata
                function loadSeek(event) {
                    console.log('loadSeek: id ' + message.id + ': set currentTime to ' + offsetS);
                    a.currentTime = offsetS;
                }
                audio.addEventListener('loadedmetadata', loadSeek, false);
                a.play();
                $('#tr-' + message.id).css('font-weight', 'bold');

                // get and show images for this artist
                echonest.artist(message.artists[0]).images( function(imageCollection) {
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
            }, whenMs);

            console.log('load: id ' + message.id + ': scheduled play at ' + whenMs + ' epoch msec in ' + remainingMs + ' msec');
        }

        if (message.command == 'setFlavors') {
            console.log('setting flavors');
            $.each(message.flavors, function(key, value) {
                console.log('setting flavor key ' + key + ', value ' + value);
                name = value[0];
                desc = value[1];
                $('#controls > tbody > tr > td > #flavors').append(
                    $('<option>', { value : name }).text(desc));
            });
        }

        // FIXME: currently not used
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
        //ws.send({command: 'Test data'});
    };

    ws.onerror = function(evt) {
        $('#conn_status').html('<b>Error</b>');
    };

    ws.onclose = function(evt) {
        $('#conn_status').html('<b>Closed</b>');
    };

    // hook up the buttons
    $('#controls > tbody > tr > td > #playlist').bind('click', function() {
        console.log('clicked');

        // remove all newer audio objects not yet playing
        // FIXME: this should probably done to us by the server instead
        $('#audio > tbody > tr').each(
            function(i, n) {
                id = $(n)[0].id;
                count = Number(id.substr(3))
                if (count > playingId) {
                    console.log('Removing track ' + count);
                    $(n).remove();
                }
            }
        );

        flavor = $('#controls > tbody > tr > td > #flavors').val();
        console.log('rescheduling with flavor ' + flavor);

        ws.send(JSON.stringify({
            'command': 'reschedule',
            'since': playingId + 1,
            'flavor': flavor
        }));
        //ws.send('{ "command": "reschedule" }');
    });
});
