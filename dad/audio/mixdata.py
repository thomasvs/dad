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

from dad.audio import common, level

class MixData(object):
    """
    I am an object holding all relevant data for mixing.

    @ivar start:         the start time for this track
    @ivar end:           the end time for this track
    @ivar peak:          the peak dB for this track
    @ivar rms:           the rms between start and end
    @ivar rmsPercentile: the 95 percentile rms in dB
    @ivar rmsPeak:       the rms in dB weighted between mix points
    @ivar rmsWeighted:   the rms in dB weighted between mix points
    @ivar attack:        the attack
    @ivar decay:         the decay
    """
    start = None
    end = None
    peak = None
    rms = None
    rmsPercentile = None
    rmsPeak = None
    rmsWeighted = None
    attack = None
    decay = None

def fromLevels(rms, peak):
    """
    @rtype: L{MixData}
    """
    assert rms.start() == peak.start(), \
        "rms %r and peak %r don't start at same time" % (
            rms.start(), peak.start())
    assert rms.end() == peak.end(), \
        "rms %r and peak %r don't end at same time" % (
            rms.end(), peak.end())

    rms = rms.convert(scale=level.SCALE_DECIBEL)
    peak = peak.convert(scale=level.SCALE_DECIBEL)

    m = MixData()
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
