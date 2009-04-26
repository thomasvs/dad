# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys
import random
import optparse

import pickle

import gobject
gobject.threads_init()

import pygst
pygst.require("0.10")
import gst

from dad.gstreamer import jukebox
from dad.audio import mixing, common
from dad.extern.log import log

_TEMPLATE = gst.PadTemplate('template', gst.PAD_SINK, gst.PAD_ALWAYS,
    gst.caps_from_string('audio/x-raw-int; audio/x-raw-float'))

class Main(object):
    def __init__(self, loop, tracks, options):
        """
        @param tracks: dict of path -> list of mixdata
        @type  tracks: dict of str -> list of L{dad.audio.mixing.MixData}
        """

        self._loop = loop
        self._tracks = tracks
        self._jukebox = jukebox.JukeboxSource()
        self._pipeline = gst.Pipeline()

        self._identity = gst.element_factory_make('identity')
        # self._identity.connect('notify::last-message',
        #    lambda o, a: sys.stdout.write(
        #        '%r\n' % self._identity.props.last_message))
        self._identity.props.single_segment = True

        ac = gst.element_factory_make('audioconvert')
        queue = gst.element_factory_make('queue')
        
        # parse the sink as a bin, linking to the unconnected pad
        sink = gst.parse_launch('bin. ( %s )' % options.sink)
        # FIXME: changed to find_unlinked_pad in gstreamer 0.10.20
        pad = sink.find_unconnected_pad(gst.PAD_SINK)
        gpad = gst.GhostPad('ghost', pad)
        sink.add_pad(gpad)

        self._pipeline.add(self._jukebox, ac, self._identity, queue, sink)
        self._jukebox.link(ac)
        ac.link(self._identity)
        self._identity.link(queue)
        queue.link(sink)

        # pick songs
        files = tracks.keys()
        if options.playlist:
            files = open(options.playlist).readlines()

        if options.random:
            paths = [random.choice(files) for i in range(options.count)]
        else:
            paths = files[:options.count]

        for path in paths:
            path = path.strip()
            try:
                self._jukebox.add_track(path, self._tracks[path][0])
            except KeyError:
                print "%s not in pickle, skipping" % path

    def start(self):
        print 'starting'
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._message_cb)
        self._pipeline.set_state(gst.STATE_PLAYING)
        print 'started'
        gobject.timeout_add(500, self._jukebox.work)
        gobject.timeout_add(500, self.work)

    def work(self):
        pad = self._identity.get_pad('src')
        try:
            position, format = pad.query_position(gst.FORMAT_TIME)
            sys.stdout.write('\roverall position: %s' % gst.TIME_ARGS(position))
            sys.stdout.flush()
        except Exception, e:
            print 'main: exception', e
            sys.stdout.flush()

        return True
  

    def _message_cb(self, bus, message):
        if message.src == self._pipeline:
            print message
            pass

        if message.src == self._identity:
            print message

def main():
    log.init('DAD_DEBUG')

    parser = optparse.OptionParser()

    default = 100
    parser.add_option('-c', '--count',
        action="store", dest="count",
        help="how many tracks to play (defaults to %d)" % default,
        default=default)
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

    opts, args = parser.parse_args(sys.argv[1:])

    if len(args) < 1:
        print 'Please give a tracks pickle path'

    tracks = pickle.load(open(args[0]))

    loop = gobject.MainLoop()

    main = Main(loop, tracks, opts)

    main.start()
    print 'going into main loop'
    loop.run()

main()    