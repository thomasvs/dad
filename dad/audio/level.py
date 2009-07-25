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

from dad.audio import common

SCALE_RAW, SCALE_DECIBEL = range(2)
SECOND = 10L ** 9

class Level(list):
    """
    I am a list that represents a list of time, value points.

    I take a list of (long, float) tuples.
    """

    def __init__(self, sequence=None, start=0L, scale=SCALE_RAW):
        """
        @param sequence: sequence of (nanoseconds, value) tuples
        @type  sequence: sequence of (long, float) tuples
        @param start:    start time of the first interval
        @type  start:    long
        @param scale:    scale of level (RAW or DB)
        @type  scale:    int
        """
        if sequence is None:
            sequence = []

        list.__init__(self, sequence)

        self._start = start
        self._scale = scale

    def __repr__(self):
        return "<Level from %r to %r>" % (self.start(), self.end())

    def start(self):
        """
        Get the start time of the first block.

        @rtype: long
        """
        return self._start

    def end(self):
        """
        Get the end time of the last block.

        @rtype: long
        """
        try:
            return self[-1][0]
        except IndexError:
            return None

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

        return Level(l, start=self.start(), scale=scale)

    def max(self):
        """
        Return the maximum value as a (time, value) tuple.
        """
        def getValue(item):
            return item[1]

        return max(self, key=getValue)

    def percentile(self, percent=95, start=None, end=None):
        """
        Get the percentile value requested.
        
        Returns the highest value of the bottom percent.
        """
        l = self.trim(start, end)

        values = [t[1] for t in l]
        values.sort()
        index = int(len(values) * percent / 100.0)

        return values[index]

    def rms(self, start=0L, end=None):
        """
        Return the RMS value over the given interval.
        """
        if end is None:
            end = self.end()

        l = self.convert(SCALE_RAW)

        squaresum = 0.0
        for endtime, value in l:
            if endtime < start:
                continue
            if endtime > end:
                continue
            squaresum += value * value
            
        ret = math.sqrt(squaresum / len(l))
        if self._scale == SCALE_DECIBEL:
            ret = common.rawToDecibel(ret)
            
        return ret
         

    def trim(self, start=None, end=None):
        """
        Return a trimmed level with the given start and end, inclusive.

        @rtype: L{Level}
        """
        if start is None and end is None:
            return self

        if start is None:
            start = 0L

        if end is None:
            end = self.end()

        first = None
        last = None
        for i, (endtime, value) in enumerate(self):
            if first is None and endtime > start:
                first = i
                # get the start time of this trim
                if i == 0:
                    start = 0L
                else:
                    # start of trim is end of previous slice
                    start = self[i - 1][0]
            if last is None and endtime >= end:
                last = i

        return Level(self[first:last + 1], start=start, scale=self._scale)


    def slice(self, delta=5 * SECOND, threshold=None):
        """
        Find all slices of the track that have their value over the given
        threshold for at least the given delta.

        If start or end point of a slice is within delta of beginning or end
        of the track, then it gets reset to beginning or end of track.

        @param threshold: the threshold for slice detection; should be in
                          the same scale as the object.  If not given, the
                          equivalent of -90 dB is used.

        @rtype:   list of L{Level}
        @returns: list of slices with their start and end point.
        """
        ret = []

        if threshold is None:
            threshold = -90
            if self._scale == SCALE_RAW:
                threshold = common.decibelToRaw(threshold) 

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
                last = self.end()
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
                    ret.append(self.trim(start, end))

        # make sure we finish even if there's not enough data left
        if state in (ABOVE, FALLING):
            self._log('appending section from %r to %r' % (start, endtime))
            ret.append(self.trim(start, endtime))

        return ret

    def attack(self, start=None, end=None):
        """
        Analyse attack of level, listing the times at which the track
        reaches each RMS level for the first time.

        @rtype: list of (value, time) tuples
        """
        lastTime = 0L
        lastValue = -98 # digital silence at 16 bit

        l = self.trim(start, end).convert(SCALE_DECIBEL)

        # start from the front
        ins = [(lastValue, lastTime), ]
        for time, rmsdB in l:
            rounded = 0 - int(0 - rmsdB) # we crossed -4 when we're at -3.5
            if rounded > lastValue:
                ins.append((rmsdB, time))
                lastTime = time
                lastValue = rounded

        return Attack(ins)

    def decay(self, start=None, end=None):
        """
        Analyse decay of level, listing the times at which the track
        reaches each RMS level for the last time.

        @rtype: list of (value, time) tuples
        """
        l = self.trim(start, end).convert(SCALE_DECIBEL)
        l.reverse()

        lastTime = l[0][0]
        lastValue = -98 # digital silence at 16 bit


        # start from the back
        ins = [(lastValue, lastTime), ]
        for time, rmsdB in l:
            rounded = 0 - int(0 - rmsdB) # we crossed -4 when we're at -3.5
            if rounded > lastValue:
                ins.append((rmsdB, time))
                lastTime = time
                lastValue = rounded

        return Attack(ins)


    def _log(self, message):
        return
        import sys
        sys.stdout.write(message + '\n')

class Attack(list):
    """
    I am a list that represents a list of value (dB), time points.

    I take a list of (float, long) tuples.
    """

    def __init__(self, sequence=None):
        """
        @param sequence: sequence of (value, nanoseconds) tuples
        @type  sequence: sequence of (float, long) tuples
        """
        if sequence is None:
            sequence = []

        list.__init__(self, sequence)

    def get(self, value):
        """
        Return the first time that matches or exceeds the given value.

        @rtype: long
        """
        for v, endtime in self:
            if v >= value:
                return endtime

        return None


