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

"""
Classes related to mixing calculations.
"""

from dad.extern.log import log

from dad.audio import level


class TrackMix(object):
    """
    I am an object holding all relevant data for mixing.

    @ivar start:         the start time for this track, in nanoseconds.
    @ivar end:           the end time for this track, in nanoseconds.
    @ivar peak:          the peak dB for this track
    @ivar rms:           the rms between start and end
    @ivar rmsPercentile: the 95 percentile rms in dB
    @ivar rmsPeak:       the rms in dB weighted between mix points
    @ivar rmsWeighted:   the rms in dB weighted between mix points
    @ivar attack:        the attack
    @type attack:        L{level.Attack}
    @ivar decay:         the decay
    @type decay:         L{level.Attack}
    """
    name = None

    start = None
    end = None
    peak = None
    rms = None
    rmsPercentile = None
    rmsPeak = None
    rmsWeighted = None
    attack = None
    decay = None

    def getVolume(self, rmsTarget=-15.0):
        """
        @param rmsTarget: the target RMS to adjust for, in dB.
        @type  rmsTarget: float

        @returns: the amount of dB to adjust by to reach the rmsTarget.
        @rtype:   float
        """
        ret = rmsTarget - self.rmsPercentile
        if ret > -self.peak:
            log.warning('trackmix', 'Track %r should be adjusted %r dB '
                'but only has headroom of %r dB',
                    self.name, ret, -self.peak)
            ret = -self.peak
        else:
            log.debug('trackmix', 'Track %r should have a %r dB adjustment',
                self.name, ret)

        return ret

def fromLevels(rms, peak):
    """
    @type  rms:  L{level.Level}
    @type  peak: L{level.Level}

    @rtype: L{TrackMix}
    """
    assert rms.start() == peak.start(), \
        "rms %r and peak %r don't start at same time" % (
            rms.start(), peak.start())
    assert rms.end() == peak.end(), \
        "rms %r and peak %r don't end at same time" % (
            rms.end(), peak.end())

    rms = rms.convert(scale=level.SCALE_DECIBEL)
    peak = peak.convert(scale=level.SCALE_DECIBEL)

    m = TrackMix()
    m.start = rms.start()
    m.end = rms.end()
    m.rms = rms.rms()
    m.rmsPercentile = rms.percentile()
    m.rmsPeak = rms.max()[1]
    # weight 9 dB below max
    m.attack = rms.attack()
    m.decay = rms.decay()
    start = m.attack.get(m.rmsPeak - 9)
    end = m.decay.get(m.rmsPeak - 9)
    m.rmsWeighted = rms.rms(start=start, end=end)
    
    m.peak = peak.max()[1]

    return m


class Mix(object, log.Loggable):
    """
    @ivar  volume1: volume adjustment for track 1, in dB.
    """

    def __init__(self, trackMix1, trackMix2, rmsTarget=-15):
        """
        Define the mix for from track 1 to track 2.

        All time values will be relative to trackMix2.start
        """
        THRESHOLD = -9 # where to pick the mix point, relative to rmsTarget

        # figure out volume adjustments
        self.volume1 = trackMix1.getVolume(rmsTarget)
        self.volume2 = trackMix2.getVolume(rmsTarget)

        level1 = rmsTarget + THRESHOLD - self.volume1
        self.debug('Finding decay point in track 1 for %f dB', level1)
        if not trackMix1.decay:
            self.warning('track mix 1 does not have decay')
            mix1 = max(trackMix1.end - 5 * 10 ** 9, trackMix1.start)
        else:
            mix1 = trackMix1.decay.get(level1)
        self.debug('Found decay point at %.3f seconds in track 1',
            mix1 / float(10 ** 9))

        level2 = rmsTarget + THRESHOLD - self.volume2
        self.debug('Finding attack point for %f dB', level2)
        if not trackMix2.attack:
            self.warning('track mix 2 does not have attack')
            mix2 = min(trackMix2.start + 5 * 10 ** 9, trackMix2.end) # to come out with leadin 0
        else:
            mix2 = trackMix2.attack.get(level2)
        self.debug('Found attack point at %.3f seconds in track 2',
            mix2 / float(10 ** 9))

        self.leadout = trackMix1.end - mix1
        self.leadin = mix2 - trackMix2.start

        # mix duration is where the two overlap
        self.duration = self.leadout + self.leadin
        self.debug('Mix overlaps for %.3f seconds',
            self.duration / float(10 ** 9))
