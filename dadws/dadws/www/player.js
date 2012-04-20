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

var decibelToRaw = function(db) {
    return Math.pow(10, db / 10.0);
}

var logTime = function() {
    var d = new Date();
    return d.logTime();
};

var mylog = function(line) {
    console.log(logTime() + ' ' + line);
};

var debugTimeRanges = function(tr) {
    var d = 'TimeRanges of length ' + tr.length;

    if (tr.length) {
        d += ' (';
        for (var i = 0; i < tr.length; ++i) {
            d += ' [' + i + '] ' +
                tr.start(i) + ' - ' + tr.end(i);
        }
        d += ')';
    }
    return d;
};

var getEnumMap = function(object, prefix) {
    var map = {};

    for (name in object) {
        if (name.substr(0, prefix.length) == prefix) {
            map[object[name]] = name;
        }
    }

    return map;
 };

var debugAudio = function(audio) {
    var READY_STATES = getEnumMap(audio, 'HAVE_');
    var NETWORK_STATES = getEnumMap(audio, 'NETWORK_');

    s = 'duration ' + audio.duration +
        ', currentTime ' + audio.currentTime +
        ', volume ' + audio.volume +
        ', paused ' + audio.paused +
        ', ended ' + audio.ended +
        ', initialTime ' + audio.initialTime +
        ', startTime ' + audio.startTime +
        ', networkState ' + NETWORK_STATES[audio.networkState] +
        ', readyState ' + READY_STATES[audio.readyState] +
        ', buffered ' + debugTimeRanges(audio.buffered) +
        ', seekable ' + debugTimeRanges(audio.seekable) +
        ', played ' + debugTimeRanges(audio.played);

    return s;
};

// Move these functions to a separate scope ?
// we can only seek after we have metadata
var loadSeek = function(id, audio, offsetS) {
    console.log('%s [%d] loadSeek: set currentTime to %f',
        logTime(), id, offsetS);
    audio.currentTime = offsetS;
    audio.play();
    console.log('%s [%d] loadSeek: %s',
        logTime(), id, debugAudio(audio));
    //a.buffered.each(function(b) {
    //    mylog(b.begin + '-' + b.end);
    //});
};

// An object that can display artist-related images in the background
var Imager = function(args) {
    var options = {
        ECHONEST_API_KEY: 'N6E4NIOVYMTHNDM8J',
        enabled: true
    };

    if (args) {
        for (var arg in args) {
            if (args[arg]) {
                options[arg] = args[arg];
            }
        }
    }

    var echonest = new EchoNest(options.ECHONEST_API_KEY);


    // public API
    return {
        show: function(artistName) {
            if (!options.enabled) return;

            echonest.artist(artistName).images(
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
        },
        disable: function() {
            options.enabled = false;
        },
        enable: function() {
            options.enabled = true;
        }
    };
};

// a WebSocket channel that forwards command messages and can send them back
var WSChannel = function(args) {
    var options = {
        url: null,
        handler: null
    };

    if (args) {
        for (var arg in args) {
            if (args[arg]) {
                options[arg] = args[arg];
            }
        }
    }

    var ws;

    if (typeof MozWebSocket != 'undefined') {
        ws = new MozWebSocket(options.url);
    } else {
        ws = new WebSocket(options.url);
    }

    ws.onmessage = function(evt) {
        console.log('ws: message: ' + evt.data);
        var message = jQuery.parseJSON(evt.data);
        options.handler['command_' + message.command](message);
    };

    // public API
    return {
        getWebSocket: function() {
            return ws;
        },
        send: function(message) {
            ws.send(JSON.stringify(message));
        }
    };
};

// the player slaved to the webchannel
var Player = function(args) {
    var playingId = 0;
    var channel = null;
    var imager = new Imager();
    //imager.disable();


    // public API
    return {
        setChannel: function(arg) {
            channel = arg;
        },
        command_load: function(message) {

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
                    'play at %f dB after %f msec since document start',
                    logTime(), message.id,
                    message.volume, (new Date().getTime() - document.start));
                a.volume = decibelToRaw(message.volume);
                // store this so we can set it back when unmuting
                a.requestedVolume = a.volume;
                console.log('%f dB is %f absolute', message.volume, a.volume);

                var offsetS = message.offset;
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

                audio.addEventListener('loadedmetadata',
                    function(event) {
                        loadSeek(message.id, a, offsetS);
                    }, false);

                //audio.addEventListener('canplaythrough', loadSeek, false);
                a.play();
                a.pause();

                $('#tr-' + message.id).css('font-weight', 'bold');

                // get and show images for this artist
                imager.show(message.artists[0]);

            }, whenMs);

            console.log('%s [%d] at.at: ' +
                'scheduled play at %f epoch msec in %f msec',
                logTime(), message.id, whenMs, remainingMs);
        },
        command_setFlavors: function(message) {
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
        },

        // FIXME: currently not used
        command_play: function(message) {
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
        },

        reschedule: function() {
            // remove all newer audio objects not yet playing
            // FIXME: this should probably done to us by the server instead
            $('#audio > tbody > tr').each(

            function(i, n) {
                id = $(n)[0].id;
                count = Number(id.substr(3));
                if (count > playingId) {
                    console.log('%s [%d] removing track',
                        logTime(), count);
                    $(n).remove();
                }
            });

            flavor = $('#controls > tbody > tr > td > #flavors').val();
            mylog('rescheduling with flavor ' + flavor);

            channel.send(JSON.stringify({
                'command': 'reschedule',
                'since': playingId + 1,
                'flavor': flavor
            }));
            //ws.send('{ "command": "reschedule" }');
        }

    };
};

$(document).ready(function() {
    document.audios = {};
    document.start = new Date().getTime();

    mylog('Document ready at ' + document.start);

    $('#clock').clock({
        'timestamp': new Date().getTime()
    });

    var player = new Player();
    var url = 'ws' + document.URL.slice(4) + 'test';
    var channel = new WSChannel({ 'url': url, 'handler': player });
    player.setChannel(channel);

    var ws = channel.getWebSocket();

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
        player.reschedule();
    });
});
