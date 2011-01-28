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
from dadgst.gstreamer import sources
from dad.common import scheduler

_TEMPLATE = gst.PadTemplate('template', gst.PAD_SRC, gst.PAD_ALWAYS,
    gst.caps_from_string('audio/x-raw-int; audio/x-raw-float'))

SCHEDULE_DURATION = gst.SECOND * 1800

class JukeboxSource(gst.Bin):
    """
    I am an audio source that outputs mixed tracks as a player would.

    I use a scheduler to decide what part of a file to play when.
    """
    # FIXME: signals not emitted yet
    # signal when a song is started
    pygobject.gsignal('started', object)
    # signal when the mix changes from one track to the next
    pygobject.gsignal('mixed', str, str)

    def __init__(self, scheduler):
        gst.Bin.__init__(self)

        self._scheduler = scheduler
        self._scheduler.connect('scheduled', self._scheduled_cb)
        
        self._added = [] # list of (path, trackmix) added
        self._scheduled = [] # list of (path, trackmix) tuples to be played
        self._playing = [] # list of (path, trackmix) tuples playing
        self._done = [] # list of (path, trackmix) tuples played

        self._addedCount = 0

        self._position = 0L
        self._lastend = 0L

        self._composition = gst.element_factory_make('gnlcomposition')
        self.add(self._composition)

        self._composition.connect('pad-added', self._composition_pad_added_cb)

        self._gpad = gst.ghost_pad_new_no_target_from_template('src', _TEMPLATE)
        self.add_pad(self._gpad)

        self._scheduling = False

        self._probes = {}

    def _composition_pad_added_cb(self, composition, pad):
        self.info('composition pad added %r' % pad)
        # FIXME: this happens for example without audioconvert,
        # source in float, sink in int, and should fail more clearly
        if not self._gpad.set_target(pad):
            self.error('Could not set target on ghost pad')
        self._gpad.set_active(True)



    def _stats(self):
        self.info('%d tracks added, %d tracks composited, %d tracks played' % (
            len(self._added), len(self._playing), len(self._done)))

    def _scheduled_cb(self, scheduler, scheduled):
        self.info('jukebox: scheduled %r' % scheduled)
        self._scheduling = False
        self.debug('scheduled %r' % scheduled)

        audiosource, gnlsource = self._makeGnlSource(scheduled.path,
            scheduled.path, volume=common.decibelToRaw(scheduled.volume))
        self._setGnlSourceProps(gnlsource, scheduled.start,
            scheduled.mediaStart, scheduled.duration)
        self.debug('adding %r' % gnlsource)
        self._composition.add(gnlsource)
        self._playing.append((scheduled, audiosource, gnlsource))

        # add a buffer probe so we can signal started
        pad = audiosource.get_pad('src')
        self._probes[pad] = pad.add_buffer_probe(self._buffer_probe)


        # if this track gets scheduled before lastend, we need an adder
        if scheduled.start < self._lastend:
            start = scheduled.start
            duration = self._lastend - scheduled.start

            self.debug('schedule adder at %r for %r' % (
                gst.TIME_ARGS(start), gst.TIME_ARGS(duration)))
            operation = gst.element_factory_make("gnloperation")
            adder = gst.element_factory_make("adder")
            operation.add(adder)
            #operation.props.sinks = 2
            operation.props.sinks = 2
            operation.props.start = start
            operation.props.duration = duration
            operation.props.priority = 0
            self._composition.add(operation)

        # update lastend
        self._lastend = scheduled.start + scheduled.duration
        self.debug('jukebox: lastend updated to %r' % 
            gst.TIME_ARGS(self._lastend))
           
    def _setGnlSourceProps(self, gnlsource, start, media_start, duration, priority=1):
        # pygobject doesn't error out when setting a negative long on a UINT64
        # see http://bugzilla.gnome.org/show_bug.cgi?id=577999
        assert start >= 0, "start is negative and shouldn't be"

        gnlsource.props.start = start
        gnlsource.props.media_start = media_start
        gnlsource.props.duration = duration
        gnlsource.props.media_duration = duration
        gnlsource.props.priority = priority

    def _buffer_probe(self, pad, buffer):
        # called once on first buffer from composition to signal started
        self.debug('first buffer on pad %r' % pad)

        audiosource = pad.get_parent()
        scheduled = None

        for s, a, g in self._playing:
            if a == audiosource:
                scheduled = s

        if scheduled:
            self.info('Scheduled %r started' % scheduled)
            self.emit('started', scheduled)
        else:
            self.warning('Got buffer on unknown gnlsource %r' % gnlsource)

        pad.remove_buffer_probe(self._probes[pad])
        del self._probes[pad]

        # let buffer pass
        return True


    def next(self):
        """
        Skip to the next track.
        """

    def work(self):
        """
        Schedule me regularly to make sure cleanups and other things happen.
        """
        self.debug('work()')

        # get our own position
        pad = self.get_pad('src')
        try:
            res = pad.query_position(gst.FORMAT_TIME)

            if res != None:
                position, format = res
            else:
                # for example, when not yet playing
                position = 0L
                format = gst.FORMAT_TIME

            # print 'internal overall position', gst.TIME_ARGS(position)
            if position >= self._position:
                self._position = position
                if self._lastend - self._position < SCHEDULE_DURATION:
                    self.debug('work(): Need to schedule some more')
                    # only ask once at a time
                    if not self._scheduling:
                        self.info('jukebox: asking scheduler to schedule')
                        self._scheduling = True
                        self._scheduler.schedule()
                    else:
                        self.debug('already waiting on a scheduler answer')
                    # FIXME:
            else:
                self.warning('position reported went down to %r' % position)
        except Exception, e:
            print 'exception querying overall position', e
        
        
        # report position of tracks
        for (i, entry) in enumerate(self._playing[:]):
            (scheduled, audiosource, gnlsource) = entry
            pad = audiosource.get_pad('src')
            if not pad:
                # pad not created yet
                continue
            # resetting otherwise when except triggers after removing,
            # the new track gets removed
            position = None
            format = None
            try:
                position, format = pad.query_position(gst.FORMAT_TIME)
                self.log('%s: %r' % (scheduled.path, gst.TIME_ARGS(position)))
            except (TypeError, gst.QueryError):
                # can happen if the track is not playing yet
                # sys.stderr.write('position query failed, path %s\n' % path)
                self.log('could not query %s' % scheduled.path)
            # FIXME: position ends up -1 at end, while gst.CLOCK_TIME_NONE is
            # positive
            # FIXME: cleaning up provokes all sorts of nastiness
            if position == gst.CLOCK_TIME_NONE or position == -1:
                self.log('should clean up %s' % scheduled.path)
            if False:
                print 'cleaning up', scheduled.path
                # clean up
                self._composition.remove(gnlsource)
                gnlsource.set_state(gst.STATE_NULL)
                audiosource.set_state(gst.STATE_NULL)
                del self._playing[i]

        return True
   
    def _makeGnlSource(self, name, path, volume=1.0):
        # volume is in raw
        caps = gst.caps_from_string('audio/x-raw-int;audio/x-raw-float')
        gnlsource = gst.element_factory_make("gnlsource",
            "%08x-%s" % (self._addedCount, name))
        self._addedCount += 1
        gnlsource.props.caps = caps

        # FIXME: maybe use something with uridecodebin instead
        audiosource = sources.AudioSource(path)
        audiosource.set_volume(volume)
        gnlsource.add(audiosource)
        return audiosource, gnlsource
gobject.type_register(JukeboxSource)
