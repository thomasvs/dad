# -*- Mode: Python; test-case-name: dad.test.test_gstreamer_leveller -*-
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

import unittest

import math

import gst

from dad.audio import level, common
from dad.common import garbage
from dad.gstreamer import leveller

class LevellerTest(garbage.GarbageTrackerTest):

    trackedTypes = [gst.Object, gst.MiniObject]

    def setUp(self):
        garbage.GarbageTrackerTest.setUp(self)
        self._leveller = leveller.Leveller('/tmp')
        # cheat and put values in here
        self._half_dB = common.rawToDecibel(0.5)
        self._quarter_dB = common.rawToDecibel(0.25)
        self._leveller.rmsdBs = [
            level.Level(
                sequence=[(level.SECOND, self._half_dB)],
                scale=level.SCALE_DECIBEL),
            level.Level(
                sequence=[(level.SECOND, self._quarter_dB)],
                scale=level.SCALE_DECIBEL),
        ]

    def tearDown(self):
        del self._leveller
        garbage.GarbageTrackerTest.tearDown(self)

    def test_get_rms_dB_one(self):
        dB = self._leveller.get_rms_dB(channel=1)
        self.assertEquals(len(dB), 1)
        time, value = dB[0]
        self.assertEquals(time, level.SECOND)
        self.assertEquals(value, self._quarter_dB)

    def test_get_rms_dB_all(self):
        dB = self._leveller.get_rms_dB()
        self.assertEquals(len(dB), 1)
        time, value_dB = dB[0]
        self.assertEquals(time, level.SECOND)
        value = common.decibelToRaw(value_dB)
        # ms is ((1/2) ** 2 + (1/4) ** 2) / 2 = 5/32
        # to avoid float rounding errors, compare against 5/32 by multiplying
        # and inting
        self.assertEquals(int(value ** 2 * 32), 5)
