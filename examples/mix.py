# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import optparse
import sys
import random
import pickle

import gobject
gobject.threads_init()

import pygst
pygst.require("0.10")
import gst

from dad.gstreamer import sources
from dad.audio import mixing, common
from dad.extern.log import log


class Mix(object):
    def __init__(self, loop, tracks, options, path1=None, path2=None):
        """
        @param tracks: dict of path -> list of mixdata
        @type  tracks: dict of str -> list of L{dad.audio.mixing.MixData}
        """

        self._loop = loop
        self._tracks = tracks
        self._pipeline = gst.parse_launch(
            'gnlcomposition name=composition ! '
            'audioconvert ! %s' % options.sink)
        self._composition = self._pipeline.get_by_name('composition')
        if not path1:
            path1 = random.choice(self._tracks.keys())
        if not path2:
            path2 = random.choice(self._tracks.keys())
        self._path1 = path1
        self._path2 = path2

    def _makeGnlSource(self, name, path, volume=1.0):
        # gnlfilesource has queue problems
        # gnlfilesrc has queue/decodebin problems causing glitches
        if False:
            gnlsource = gst.element_factory_make("gnlfilesource", name)
            gnlsource.props.location = path
            return gnlsource
        
        caps = gst.caps_from_string('audio/x-raw-int;audio/x-raw-float')
        gnlsource = gst.element_factory_make("gnlsource", name)
        gnlsource.props.caps = caps

        audiosource = sources.AudioSource(path)
        audiosource.set_volume(volume)
        #audiosource = gst.element_factory_make("uridecodebin")
        #audiosource.props.uri = 'file://' + path
        #uri = 'file://' + path
        #decodebin = singledecodebin.SingleDecodeBin(caps=caps, uri=uri)
        #source.add(decodebin)
        gnlsource.add(audiosource)
        return audiosource, gnlsource

    def setup(self):
        EXTRA = 5 * gst.SECOND # how much of tracks to play outside of mix

        # set up the mix
        track1 = self._tracks[self._path1][0]
        if not track1.name: track1.name = self._path1
        track2 = self._tracks[self._path2][0]
        if not track2.name: track2.name = self._path2

        mix = mixing.Mix(track1, track2)

        print 'Track 1: %s' % self._path1
        print '- from %s to %s' % (
            gst.TIME_ARGS(track1.start), gst.TIME_ARGS(track1.end))
        print '- leadout at %s for %s' % (
            gst.TIME_ARGS(track1.end - mix.leadout), gst.TIME_ARGS(mix.leadout))

        print 'Track 2: %s' % self._path2
        print '- from %s to %s' % (
            gst.TIME_ARGS(track2.start), gst.TIME_ARGS(track2.end))
        print '- leadin until %s for %s' % (
            gst.TIME_ARGS(track2.start + mix.leadin), gst.TIME_ARGS(mix.leadin))

        print 'mix start:    %s' % gst.TIME_ARGS(EXTRA)
        print 'mix duration: %s' % gst.TIME_ARGS(mix.duration)

        raw = common.decibelToRaw(mix.volume1)
        print 'Adjusting track 1 by %.3f dB' % mix.volume1
        asource1, source1 = self._makeGnlSource(
            'source1', self._path1, volume=raw)

        source1.props.start = 0 * gst.SECOND
        source1.props.duration = EXTRA + mix.duration
        source1.props.media_start = track1.end - (EXTRA + mix.duration)
        source1.props.media_duration = EXTRA + mix.duration
        source1.props.priority = 1

        self._composition.add(source1)

        raw = common.decibelToRaw(mix.volume2)
        print 'Adjusting track 2 by %.3f dB' % mix.volume2
        asource2, source2 = self._makeGnlSource(
            'source2', self._path2, volume=raw)

        source2.props.start = EXTRA
        source2.props.duration = EXTRA + mix.duration
        source2.props.media_start = track2.start
        source2.props.media_duration = EXTRA + mix.duration
        source2.props.priority = 2

        self._composition.add(source2)

        self._source1 = source1
        self._asource1 = asource1
        self._source2 = source2
        self._asource2 = asource2

        # add the mixer effect
        operation = gst.element_factory_make("gnloperation")
        adder = gst.element_factory_make("adder")
        operation.add(adder)
        operation.props.sinks = 2
        operation.props.start = EXTRA
        operation.props.duration = mix.duration
        operation.props.priority = 0

        self._composition.add(operation)


    def start(self):
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._message_cb)
        print 'setting to PLAYING'
        self._pipeline.set_state(gst.STATE_PLAYING)

        gobject.timeout_add(500, self._query)

    def _query(self):
        s = self._asource2
        pad = s.get_pad('src')
        if not pad:
            # pad not created yet
            return True

        position = None
        try:
            position, format = pad.query_position(gst.FORMAT_TIME)
        except gst.QueryError:
            print 'query failed'
            sys.stderr.write('query failed\n')
            sys.stdout.flush()
            pass
        except TypeError:
            print 'no result'

        # position is returned as a gint64, not a guint64 as GstClockTime
        change, current, pending = s.get_state()
        if position == -1L and current == gst.STATE_PLAYING:
            print 'mix done'
            self._loop.quit()
        return True

    def _message_cb(self, bus, message):
        if message.src == self._pipeline:
            # print message
            pass
        if message.src not in (self._source1, self._source2):
            return

        source = 'source1'
        if message.src == self._source2:
            source = 'source2'

        if message.type == gst.MESSAGE_STATE_CHANGED:
            old, new, pending = message.parse_state_changed()
            if new == gst.STATE_PLAYING:
                print 'playing', source

def main():
    log.init('DAD_DEBUG')

    parser = optparse.OptionParser()

    parser.add_option('-p', '--playlist',
        action="store", dest="playlist",
        help="playlist to play from")
    parser.add_option('-r', '--random',
        action="store_true", dest="random",
        help="play tracks in random order")
    default = 'queue ! autoaudiosink'
    parser.add_option('-s', '--sink',
        action="store", dest="sink",
        help="GStreamer audio sink to output to (defaults to %s" % default,
        default=default)

    options, args = parser.parse_args(sys.argv[1:])


    if len(args) < 1:
        print 'Please give a tracks pickle path'

    tracks = pickle.load(open(args[0]))

    # select two files to mix
    paths = args[2:]

    if len(paths) < 2:
        missing = 2 - len(paths)
        files = tracks.keys()
        if options.playlist:
            files = open(options.playlist).readlines()

        if options.random:
            paths.extend([random.choice(files) for i in range(missing)])
        else:
            paths = files[:missing]

        paths = [path.strip() for path in paths]
    
    loop = gobject.MainLoop()

    mix = Mix(loop, tracks, options, paths[0], paths[1])
    mix.setup()

    mix.start()
    loop.run()



main()    
