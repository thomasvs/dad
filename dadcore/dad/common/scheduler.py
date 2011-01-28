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

import os
import sys
import math

import gobject

from gst.extend import pygobject

from dad.extern.log import log
from dad.audio import mixing, common

SECOND = 1000000000
SCHEDULE_DURATION = 1800 * SECOND

def TIME_ARGS(nanoseconds):
    h = nanoseconds / (SECOND * 60 * 60)
    nanoseconds -= h * SECOND * 60 * 60
    m = nanoseconds / (SECOND * 60)
    nanoseconds -= m * SECOND * 60
    s = nanoseconds / SECOND
    nanoseconds -= s * SECOND

    return "%d:%02d:%02d.%09d" % (h, m, s, nanoseconds)

class Scheduled(object):
    """
    I represent a scheduled object.

    @ivar volume: volume adjustment for track, in dB.
    @type volume: float
    """

    path = None
    trackmix = None
    number = None
    start = None
    duration = None
    mediaStart = None
    volume = 0.0

    description = None

    def __init__(self, path, trackmix, number, description=None):
        self.path = path
        self.trackmix = trackmix
        self.number = number

        self.description = description and description or os.path.basename(path)

    def __repr__(self):
        return '<scheduler.Scheduled %d for %s>' % (
            self.number, self.description)

class Scheduler(log.Loggable, gobject.GObject):
    """
    I schedule tracks for a playout system.
    I decide when which part of each file should be played, at which volume.

    I use a selecter to get tracks to schedule.

    @ivar duration: the total duration of all currently scheduled tracks
    """
    logCategory = 'scheduler'

    pygobject.gsignal('scheduled', object) # Scheduled

    duration = 0

    def __init__(self, selecter, begin=False):
        """
        @param begin: whether to play first track from beginning.
        """
        gobject.GObject.__init__(self)

        self._added = [] # list of Scheduled
        self._scheduled = {} # hash of number -> Scheduled

        self._counter = 0 # counter for how many tracks where added
        self._lastScheduled = 0 # counter for last track that was scheduled

        self._position = 0L

        self._begin = begin
        self._selecter = selecter

    def _stats(self):
        self.info('%d tracks added, %d tracks composited, %d tracks played' % (
            len(self._added), len(self._playing), len(self._done)))

    def add_track(self, path, trackmix):
        """
        Add the given track to the schedule queue.

        @param path:     path to the track to play
        @type  path:     str
        @type  trackmix: L{mixing.TrackMix}

        @rtype: the scheduled track's number
        """
        assert isinstance(trackmix, mixing.TrackMix)

        self.debug('Adding track %d: %s', self._counter, path)
        
        s = Scheduled(path, trackmix, self._counter)
        self._added.append(s)
        self._counter += 1

        self._process()

        return s

    def _schedule(self, scheduled, start, duration):
        """
        @type  scheduled: L{Scheduled}
        @type  start:     int
        @param start:     at what playing time should start, in nanoseconds
        @param duration:  how much of the track to play, in nanoseconds
        """
        scheduled.start = start
        scheduled.duration = duration
        scheduled.mediaStart = scheduled.trackmix.end - duration
        scheduled.volume = scheduled.trackmix.getVolume()
        self._scheduled[scheduled.number] = scheduled
        self._lastScheduled = scheduled.number

        self.debug('scheduled track %d, start %r, duration %r, mediaStart %r',
            scheduled.number, TIME_ARGS(scheduled.start),
            TIME_ARGS(scheduled.duration),
            TIME_ARGS(scheduled.mediaStart),
            )
        self.duration = scheduled.start + scheduled.duration
        self.debug('scheduled audio until %r', TIME_ARGS(self.duration))
        self.debug('emitting scheduled for %r', scheduled)
        self.emit('scheduled', scheduled)


    def _process(self):
        """
        Process as many added tracks as possible.

        For the first track, wait until we have the second track too so
        we can pick a nice point to start right before the mix.
        """


        self.debug('_process: %d to schedule, %d scheduled',
            len(self._added), len(self._scheduled.keys()))

        # process queues and set up tracks
        if not self._added:
            self.debug('no tracks added to schedule')
            # can't do anything
            return

        if len(self._scheduled.keys()) < 1:
            # we need at least two tracks to start
            if len(self._added) < 2:
                self.info('Waiting for 2 added tracks before we schedule anything')
                return

            first = self._added[0]
            self.info('starting with %s' % first.path)
            del self._added[0]

            next = self._added[0]
            if self._begin:
                self.debug('Playing the first track completely')
                duration = first.trackmix.end - first.trackmix.start
            else:
                # Start from a position in the first track 10 seconds before the
                # mix starts
                self.debug('Playing only 10 secs of first track')
                mix = mixing.Mix(first.trackmix, next.trackmix)
                duration = mix.duration + 10 * SECOND

            self._schedule(first, 0, duration)

        # keep going
        lastScheduled = self._scheduled[self._lastScheduled]

        prev = lastScheduled.trackmix
        #while self.duration - self._position < SCHEDULE_DURATION:
        #    if not self._added:
        #        self.info('Out of added tracks, cannot schedule more')
        #        return
        while self._added:

            next = self._added[0]
            del self._added[0]
            mix = mixing.Mix(prev, next.trackmix)
            duration = next.trackmix.end - next.trackmix.start
            self._schedule(next, self.duration - mix.duration, duration)

            prev = next.trackmix

    def schedule(self):
        """
        Schedule another track.

        Called by users when they're out of scheduled tracks.
        """
        self.info('asked to schedule, asking selecter to select track')
        d = self._selecter.select()
        # FIXME: should we be doing this ourselves ?
        d.addCallback(lambda (p, t): self.add_track(p, t))
        # FIXME: we do a second one here because we need two to get started
        # but doing this always seems wrong
        d.addCallback(lambda _: self._selecter.select())
        d.addCallback(lambda (p, t): self.add_track(p, t))
        return d

gobject.type_register(Scheduler) 
