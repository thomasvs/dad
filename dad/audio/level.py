# -*- Mode: Python; test-case-name: dad.test.test_audio_level -*-
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
import gst

from dad.audio import common

SCALE_RAW, SCALE_DECIBEL = range(2)
SECOND = 10L ** 9

class Level(list):
    """
    I am a list that represents a list of time, value points.

    I take a list of (long, float) tuples.
    """

    def __init__(self, sequence=None, scale=SCALE_RAW):
        """
        @param sequence: sequence of (nanoseconds, value) tuples
        @type  sequence: sequence of (long, float) tuples
        @param scale:    scale of level (RAW or DB)
        @type  scale:    int
        """
        if sequence is None:
            sequence = []

        list.__init__(self, sequence)

        self._scale = scale

    def convert(self, scale):
        """
        Convert to the given scale.
        """
        if self._scale is scale:
            return self

        # map from current scale to converter method
        converters = {
            SCALE_RAW: common.rawToDecibel,
            SCALE_DECIBEL: common.decibelToRaw,
        }
        converter = converters[self._scale]

        l = []
        for endtime, value in self:
            l.append((endtime, converter(value)))

        return Level(l, scale=scale)

    def max(self):
        """
        Return the maximum value as a (time, value) tuple.
        """
        def getValue(item):
            return item[1]

        return max(self, key=getValue)

    def rms(self, start=None, end=None):
        """
        Return the RMS value over the given interval.
        """
        l = self.convert(SCALE_RAW)

        squaresum = 0.0
        for _, value in l:
            squaresum += value * value
            
        return math.sqrt(squaresum / len(l))

    def slice(self, delta=5 * SECOND, threshold=None):
        """
        Find all slices of the track that have their value over the given
        threshold for at least the given delta.

        If start or end point of a slice is within delta of beginning or end
        of the track, then it gets reset to beginning or end of track.

        @param threshold: the threshold for slice detection; should be in
                          the same scale as the object.  If not given, the
                          equivalent of -90 dB is used.

        @rtype:   list of (long, long) tuples
        @returns: list of slices with their start and end point.
        """
        if threshold is None:
            threshold = -90
            if self._scale == SCALE_RAW:
                threshold = common.decibelToRaw(threshold) 

        ret = []

        previous = 0L # end of previous section
        length = 0L # length of current section
        start = 0L # start of slice
        end = 0L # end of slice

        # implement a state machine with 4 states
        BELOW, CLIMBING, ABOVE, FALLING = range(4)

        state = BELOW

        for endtime, value in self:
            length = endtime - previous
            previous = endtime
            
            if state is BELOW:
                if value < threshold:
                    continue

                self._log('at %r value %r is above threshold %r' % (
                    endtime, value, threshold))
                state = CLIMBING
                
                # start of interval is start of previous block ...
                start = endtime - length

                # ... but if it's close to 0, then pick 0 instead
                if start < delta:
                    self._log('resetting start to 0')
                    start = 0L
                self._log('set start to %r' % start)
            elif state is CLIMBING:
                if value < threshold:
                    # fell again, reset
                    self._log('at %r value %r is below threshold %r' % (
                        endtime, value, threshold))
                    self._log('fell again')
                    state = BELOW
                    continue

                if endtime - start > delta:
                    # long enough, so approve
                    state = ABOVE
            elif state is ABOVE:
                if value > threshold:
                    continue

                self._log('at %r value %r is below threshold %r' % (
                    endtime, value, threshold))
                state = FALLING

                # end time of slice is end time of this section ...
                end = endtime
                # ... but if we're close to the end, then pick the end
                last = self[-1][0]
                if last - end < delta:
                    self._log('resetting end to last %r' % last)
                    end = last
 
            elif state is FALLING:
                if value > threshold:
                    # rose again, reset
                    state = ABOVE
                    continue

                if endtime - end > delta:
                    # long enough, so approve
                    state = BELOW
                    self._log('appending section from %r to %r' % (start, end))
                    ret.append((start, end))

        # make sure we finish even if there's not enough data left
        if state in (ABOVE, FALLING):
            self._log('appending section from %r to %r' % (start, endtime))
            ret.append((start, endtime))

        return ret


    def _log(self, message):
        return
        import sys
        sys.stdout.write(message + '\n')
