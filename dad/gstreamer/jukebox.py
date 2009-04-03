# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# DAD - Digital Audio Database
# Copyright (C) 2008 Thomas Vander Stichele <thomas at apestaart dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# only require pygst when we're executed instead of imported
if __name__ == '__main__':
    import pygst
    pygst.require('0.10')

import os
import sys
import math

import gobject
import gst

from gst.extend import pygobject

from dad.audio import mixing, common
from dad.gstreamer import sources

_TEMPLATE = gst.PadTemplate('template', gst.PAD_SRC, gst.PAD_ALWAYS,
    gst.caps_from_string('audio/x-raw-int; audio/x-raw-float'))

class JukeboxSource(gst.Bin):
    """
    I am an audio source that outputs mixed tracks as a player would.
    """
    # signal when a song is started
    pygobject.gsignal('started', str)
    # signal when the mix changes from one track to the next
    pygobject.gsignal('mixed', str, str)

    def __init__(self):
        gst.Bin.__init__(self)

        self._done = [] # list of (path, trackmix) tuples
        self._playing = [] # list of (path, trackmix) tuples
        self._queue = [] # list of (path, trackmix) tuples

        self._composition = gst.element_factory_make('gnlcomposition')
        self.add(self._composition)

        self._composition.connect('pad-added', self._composition_pad_added_cb)

        self._gpad = gst.ghost_pad_new_no_target_from_template('src', _TEMPLATE)
        self.add_pad(self._gpad)


    def _composition_pad_added_cb(self, composition, pad):
        self.info('composition pad added %r' % pad)
        # FIXME: this happens for example without audioconvert,
        # source in float, sink in int, and should fail more clearly
        if not self._gpad.set_target(pad):
            self.error('Could not set target on ghost pad')
        self._gpad.set_active(True)

    def add_track(self, path, trackmix):
        """
        Add the given track to the playing queue.
        """
        self.debug('Adding track %s' % path)

        self._queue.append((path, trackmix))
        self._process()

    def _process(self):
        self.debug('_process')
        # process queues and set up tracks
        if not self._queue:
            # can't do anything
            return

        if not self._playing:
            path, trackmix = self._queue[0]
            self.info('starting with %s' % path)
            del self._queue[0]

            raw = common.decibelToRaw(trackmix.getVolume())
            audiosource, gnlsource = self._makeGnlSource(path, path, volume=raw)
            start = trackmix.start
            start = trackmix.end - 20 * gst.SECOND
            duration = trackmix.end - start
            #duration = gst.SECOND * 15
            priority = 1000 - len(self._playing) * 2
            self._setGnlSourceProps(gnlsource, 0L, start, duration, priority)

            self.debug('adding %r' % gnlsource)
            self._composition.add(gnlsource)
            self._playing.append((path, trackmix, audiosource, gnlsource))
            self._lastend = trackmix.end
            self._lastend = trackmix.start + duration

        # keep going
        trackmix = self._playing[-1][1]

        prev = trackmix
        for path, trackmix in self._queue:
            # FIXME: remove from queue, add to playing
            mix = mixing.Mix(prev, trackmix)
            start = self._lastend - mix.duration
            raw = common.decibelToRaw(trackmix.getVolume())
            audiosource, gnlsource = self._makeGnlSource(path, path, volume=raw)
            duration = trackmix.end - trackmix.start
            self.info('scheduling %r at %s for %s' % (
                path, gst.TIME_ARGS(start), gst.TIME_ARGS(duration)))
            self._setGnlSourceProps(gnlsource, start, trackmix.start, duration)
            self._composition.add(gnlsource)
            self._playing.append((path, trackmix, audiosource, gnlsource))

            # add the mixer effect
            if True:
                self.debug('adding mixer')
                operation = gst.element_factory_make("gnloperation")
                adder = gst.element_factory_make("adder")
                operation.add(adder)
                #operation.props.sinks = 2
                self.debug('adding mixer at %r for %r' % (gst.TIME_ARGS(start), gst.TIME_ARGS(mix.duration)))
                operation.props.sinks = 2
                operation.props.start = start
                operation.props.duration = mix.duration
                operation.props.priority = 0
                self._composition.add(operation)


            self._lastend = start + duration
            prev = trackmix
            
        self._queue = []

            
    def _setGnlSourceProps(self, gnlsource, start, media_start, duration, priority=1):
        gnlsource.props.start = start
        try:
            gnlsource.props.duration = duration
        except Exception, e:
            import code; code.interact(local=locals())
        gnlsource.props.media_start = media_start
        gnlsource.props.media_duration = duration
        gnlsource.props.priority = priority

    def next(self):
        """
        Skip to the next track.
        """

    def work(self):
        """
        Schedule me regularly to make sure cleanups and other things happen.
        """
        self.log('work()')

        # report position of tracks
        for i, entry in enumerate(self._playing[:]):
            (path, trackmix, audiosource, gnlsource) = entry
            pad = audiosource.get_pad('src')
            if not pad:
                # pad not created yet
                continue
            # resetting otherwise when except triggers after removing,
            # the new track gets removed
            position = format = None
            try:
                position, format = pad.query_position(gst.FORMAT_TIME)
            except gst.QueryError:
                print 'query failed'
                sys.stderr.write('query failed\n')
                sys.stdout.flush()
            self.log('%s: %r' % (path, gst.TIME_ARGS(position)))
            # FIXME: position ends up -1 at end, while gst.CLOCK_TIME_NONE is positive
            # FIXME: cleaning up provokes all sorts of nastiness
            #if position == gst.CLOCK_TIME_NONE or position == -1:
            if False:
                print 'cleaning up', path
                # clean up
                self._composition.remove(gnlsource)
                gnlsource.set_state(gst.STATE_NULL)
                audiosource.set_state(gst.STATE_NULL)
                del self._playing[i]

        return True
   


    def _makeGnlSource(self, name, path, volume=1.0):
        caps = gst.caps_from_string('audio/x-raw-int;audio/x-raw-float')
        gnlsource = gst.element_factory_make("gnlsource", name)
        gnlsource.props.caps = caps

        audiosource = sources.AudioSource(path)
        audiosource.set_volume(volume)
        gnlsource.add(audiosource)
        return audiosource, gnlsource
