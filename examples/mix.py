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

from dad.audio import mixdata
from dad.extern import singledecodebin


class Mix(object):
    def __init__(self, tracks, path1=None, path2=None):
        """
        @param tracks: dict of path -> list of mixdata
        @type  tracks: dict of str -> list of L{dad.audio.mixdata.MixData}
        """

        self._tracks = tracks
        self._pipeline = gst.parse_launch(
            'gnlcomposition name=composition ! '
            'audioconvert ! queue ! autoaudiosink')
        self._composition = self._pipeline.get_by_name('composition')
        if not path1:
            path1 = random.choice(self._tracks.keys())
        if not path2:
            path2 = random.choice(self._tracks.keys())
        self._path1 = path1
        self._path2 = path2

    def _makeGnlSource(self, name, path):
        if False:
            source = gst.element_factory_make("gnlfilesource", name)
            source.props.location = path
            return source
        
        caps = gst.caps_from_string('audio/x-raw-int;audio/x-raw-float')
        uri = 'file://' + path
        decodebin = singledecodebin.SingleDecodeBin(caps=caps, uri=uri)
        source = gst.element_factory_make("gnlsource", name)
        source.add(decodebin)
        source.props.caps = caps
        return source

    def setup(self):
        EXTRA = 5 * gst.SECOND # how much of tracks to play outside of mix

        # set up the mix
        track1 = self._tracks[self._path1][0]
        track2 = self._tracks[self._path2][0]

        mix = mixdata.Mix(track1, track2)

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

        print 'mix duration: %s' % gst.TIME_ARGS(mix.duration)

        source1 = self._makeGnlSource('source1', self._path1)

        source1.props.start = 0 * gst.SECOND
        source1.props.duration = EXTRA + mix.duration
        source1.props.media_start = track1.end - (EXTRA + mix.duration)
        source1.props.media_duration = EXTRA + mix.duration
        source1.props.priority = 1

        self._composition.add(source1)

        source2 = self._makeGnlSource('source2', self._path2)

        source2.props.start = EXTRA
        source2.props.duration = EXTRA + mix.duration
        source2.props.media_start = track2.start
        source2.props.media_duration = EXTRA + mix.duration
        source2.props.priority = 2

        self._composition.add(source2)

        self._source1 = source1
        self._source2 = source2

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
        self._pipeline.set_state(gst.STATE_PLAYING)

    def _message_cb(self, bus, message):
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
    if len(sys.argv) < 2:
        print 'Please give a tracks pickle path'

    path1 = path2 = None
    if len(sys.argv) > 2:
        path1 = sys.argv[2]
    if len(sys.argv) > 3:
        path2 = sys.argv[3]

    tracks = pickle.load(open(sys.argv[1]))

    mix = Mix(tracks, path1, path2)
    mix.setup()

    loop = gobject.MainLoop()

    mix.start()
    loop.run()



main()    
