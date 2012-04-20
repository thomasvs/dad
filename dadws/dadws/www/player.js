// vi:si:et:sw=4:sts=4:ts=4

String.repeat = function(chr, count) {
    var str = '';
    for (var x = 0; x < count; ++x) { str += chr; }
    return str;
};

String.prototype.padL = function(width, pad) {
    if (!width || width < 1)
        return this;

    if (!pad) pad = ' ';
    var length = width - this.length;
    if (length < 1) return this.substr(0, width);

    return (String.repeat(pad, length) + this).substr(0, width);
};

Date.prototype.logTime = function() {
    var date = this;

    var hours = date.getHours();
    var minutes = date.getMinutes();
    var seconds = date.getSeconds();
    var ms = date.getMilliseconds();

    var disp = hours.toString().padL(2, '0') + ':' +
        minutes.toString().padL(2, '0') + ':' +
        seconds.toString().padL(2, '0') + '.' +
        ms.toString().padL(3, '0');

    return disp;
};

var logTime = function () {
    var d = new Date();
    return d.logTime();
}

var mylog = function(line) {
    var d = new Date();
    console.log(d.logTime() + ' ' + line);
};


$(document).ready(function() {
    var API_KEY = 'N6E4NIOVYMTHNDM8J';
    var echonest = new EchoNest(API_KEY);
    var playingId = 0;

    document.audios = {};
    document.start = new Date().getTime();

    mylog('Document ready at ' + document.start);

    $('#clock').clock({
        'timestamp': new Date().getTime()
    });

    var ws;
    var url = 'ws' + document.URL.slice(4) + 'test';

    if (typeof MozWebSocket != 'undefined') {
        ws = new MozWebSocket(url);
    } else {
        ws = new WebSocket(url);
    }
    ws.onmessage = function(evt) {
        mylog('ws: message: ' + evt.data);
        var message = jQuery.parseJSON(evt.data);
        if (message.command == 'load') {
            // load a new track
            console.log('%s [%d] ws: load: %s - %s',
                logTime(), message.id,
                message.artists.toString(), message.title);

            // remove a previous one with the same id
            $('#tr-' + message.id).remove();
            if (message.id in document.audios) {
            console.log('%s [%d] deleting previous audio',
                logTime(), message.id);
                delete document.audios[message.id];
            }

            // add the new one
            $('#audio > tbody:last').append(
                '<tr id="tr-' + message.id + '"><td>' +
                message.id + '</td>' +
                '<td>' + message.artists + '</td>' +
                '<td>' + message.title + '</td>' +
                '<td>' + new Date(message.when * 1000) + '</td>' +
                '<td><audio id="audio-' + message.id +
                '" src="' + message.uri + '" controls="controls"/></td></tr>');
            var audio = $('#audio-' + message.id).get(0);
            document.audios[message.id] = audio;

            // clean up when playback ends
            $('#audio-' + message.id).bind('ended', function() {
            console.log('%s [%d] ended',
                logTime(), message.id);
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
                console.log('%s [%d] at.at: ' +
                    'play after %f msec since document start',
                    logTime(), message.id,
                    (new Date().getTime() - document.start));

                offsetS = message.offset;
                console.log('%s [%d] at.at: fragment starts at %f sec',
                    logTime(), message.id, offsetS);

                if (remainingMs < 0) {
                    // FIXME: handle forwarding past the end,
                    // which plays from 0
                    offsetS += -remainingMs / 1000.0;
                    console.log('%s [%d] at.at: ' +
                        'forward track by %f sec to %f sec',
                        logTime(), message.id, (-remainingMs / 1000.0),
                        offsetS);
                }

                // we can only seek after we have metadata
                function loadSeek(event) {
                    console.log('%s [%d] loadSeek: set currentTime to %f',
                        logTime(), message.id, offsetS);
                    a.currentTime = offsetS;
                    a.play();
                    console.log('%s [%d] loadSeek: ' + 
                        ' currentTime is now %f' + 
                        ' networkState is %d' + 
                        ' readyState is %d' + 
                        ' buffered is %d',
                        logTime(), message.id, 
                        a.currentTime, a.networkState, a.readyState,
                        a.buffered.length);
                    //a.buffered.each(function(b) {
                    //    mylog(b.begin + '-' + b.end);
                    //});
                }
                audio.addEventListener('loadedmetadata', loadSeek, false);

                //audio.addEventListener('canplaythrough', loadSeek, false);
                a.play();
                a.pause();

                $('#tr-' + message.id).css('font-weight', 'bold');

                // get and show images for this artist
                echonest.artist(message.artists[0]).images(
                    function(imageCollection) {
                    var images = [];
                    for (i in imageCollection.data.images) {
                        images.push({
                            src: imageCollection.data.images[i].url,
                            fade: 3000
                        });
                    }
                    $.vegas('slideshow', {
                        delay: 10000,
                        backgrounds: images
                    })('overlay', {
                        src: 'vegas/overlays/13.png',
                        opacity: 0.5
                    });

                });
            }, whenMs);

            console.log('%s [%d] at.at: ' +
                'scheduled play at %f epoch msec in %f msec',
                logTime(), message.id, whenMs, remainingMs);
        }

        if (message.command == 'setFlavors') {
            mylog('setting flavors');
            if (message.flavors) {
                $.each(message.flavors, function(key, value) {
                    mylog('setting flavor key ' + key + ', value ' + value);
                    name = value[0];
                    desc = value[1];
                    $('#controls > tbody > tr > td > #flavors').append(
                    $('<option>', {
                        value: name
                    }).text(desc));
                });
            }
        }

        // FIXME: currently not used
        if (message.command == 'play') {
            console.log('%s [%d] at.at: ' +
                'schedule play at %f sec',
                logTime(), message.id, (message.when * 1000));
            at.at(function() {
                a = document.audios[message.id];
                console.log('%s [%d] at.at: ' +
                    'play of %o',
                    logTime(), message.id, a);
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
        mylog('clicked');

        // remove all newer audio objects not yet playing
        // FIXME: this should probably done to us by the server instead
        $('#audio > tbody > tr').each(

        function(i, n) {
            id = $(n)[0].id;
            count = Number(id.substr(3));
            if (count > playingId) {
                mylog('Removing track ' + count);
                console.log('%s [%d] removing track',
                    logTime(), count);
                $(n).remove();
            }
        });

        flavor = $('#controls > tbody > tr > td > #flavors').val();
        mylog('rescheduling with flavor ' + flavor);

        ws.send(JSON.stringify({
            'command': 'reschedule',
            'since': playingId + 1,
            'flavor': flavor
        }));
        //ws.send('{ "command": "reschedule" }');
    });
});
