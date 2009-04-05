# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys
import random

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
    def __init__(self, loop, tracks, playlist=None):
        """
        @param tracks: dict of path -> list of mixdata
        @type  tracks: dict of str -> list of L{dad.audio.mixing.MixData}
        """

        self._loop = loop
        self._tracks = tracks
        self._jukebox = jukebox.JukeboxSource()
        self._pipeline = gst.Pipeline()

        self._identity = gst.element_factory_make('identity')
        # self._identity.connect('notify::last-message', lambda o, a: sys.stdout.write('%r\n' % self._identity.props.last_message))

        print 'single', self._identity.props.single_segment
        self._identity.props.single_segment = True
        print 'single', self._identity.props.single_segment

        ac = gst.element_factory_make('audioconvert')
        queue = gst.element_factory_make('queue')
        sink = gst.element_factory_make('autoaudiosink')
        # sink = gst.parse_launch('bin. ( vorbisenc name=enc ! oggmux ! filesink location=mix.ogg )')
        #sink = gst.parse_launch('bin. ( audioconvert ! autoaudiosink )')
        #enc = sink.get_by_name('enc')
        #pad = enc.get_pad('sink')
        #gpad = gst.GhostPad('ghost', pad)
        #print sink
        #sink.add_pad(gpad)

        self._pipeline.add(self._jukebox, ac, self._identity, queue, sink)
        self._jukebox.link(ac)
        ac.link(self._identity)
        self._identity.link(queue)
        queue.link(sink)

        # pick songs
        paths = [random.choice(tracks.keys()) for i in range(3)]
        if playlist:
            lines = open(playlist).readlines()
            paths = lines[:3]

        for path in paths:
            path = path.strip()
            self._jukebox.add_track(path, self._tracks[path][0])

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
            print 'overall position', gst.TIME_ARGS(position)
        except Exception, e:
            print 'exception', e

        import sys
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

    if len(sys.argv) < 2:
        print 'Please give a tracks pickle path'

    tracks = pickle.load(open(sys.argv[1]))
    playlist = None

    if len(sys.argv) > 2:
        playlist = sys.argv[2]

    loop = gobject.MainLoop()

    main = Main(loop, tracks, playlist)

    main.start()
    print 'going into main loop'
    loop.run()



main()    
