# -*- Mode: Python; test-case-name: dad.test.test_audio_level -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import math

import unittest

from dad.audio import level, common

class LevelTest(unittest.TestCase):
    def setUp(self):
        # cheat and put values in here
        self._half_dB = common.rawToDecibel(0.5)
        self._quarter_dB = common.rawToDecibel(0.25)

    def testConvert(self):
        l = level.Level(scale=level.SCALE_RAW)
        for i in range(0, 100):
            l.append((long(i + 1), 1.0 / (i + 1)))
        dB = l.convert(level.SCALE_DECIBEL)
        l2 = dB.convert(level.SCALE_RAW)

        for i in range(0, 100):
            self.failIfAlmostEqual(l[i][1], dB[i][1])
            self.assertAlmostEqual(l[i][1], l2[i][1])

class SouthLevelTest(unittest.TestCase):
    def setUp(self):
        import pickle
        handle = open(os.path.join(os.path.dirname(__file__), 'south.pickle'))
        self._level = pickle.load(handle)

    def testMax(self):
        maxTuple = self._level.max()
        self.assertAlmostEqual(maxTuple[0], 43989841268L)
        self.assertAlmostEqual(maxTuple[1], -4.7446228530026247)

    def testRMS(self):
        self.assertAlmostEqual(self._level.rms(), 0.0843342138227)

    def testSlice(self):
        slices = self._level.slice()
        self.assertEquals(len(slices), 1)

class HomeLevelTest(unittest.TestCase):
    def setUp(self):
        import pickle
        handle = open(os.path.join(os.path.dirname(__file__), 'home.pickle'))
        self._level = pickle.load(handle)

    def testTrim(self):
        trimmed = self._level.trim(self._level.start(), self._level.end())
        self.assertEquals(trimmed.start(), self._level.start())
        self.assertEquals(trimmed.end(), self._level.end())


    def testSlice(self):
        slices = self._level.slice()
        self.assertEquals(len(slices), 2)

        first = slices[0]
        self.assertEquals(first.start(), 0L)

        second = slices[1]
        self.assertEquals(second.end(), self._level.end())

        self.failUnless(second.start() > first.end())

    def testAttack(self):
        a = self._level.attack()

        # Home Again reaches slightly above -20 dB close to 2 seconds
        self.assertEquals(a.get(-20) / level.SECOND, 1)

        self.assertEquals(a.get(-18) / level.SECOND, 4)

    def testDecayFirstSlice(self):
        slices = self._level.slice()
        
        a = slices[0].decay()

        # Home Again drops below -20 dB around 203 seconds
        self.assertEquals(a.get(-20) / level.SECOND, 203)

    def testAttackSecondSlice(self):
        slices = self._level.slice()
        
        a = slices[1].attack()
        # Bonus Track reaches slightly above -20 dB close to 228 seconds
        self.assertEquals(a.get(-20) / level.SECOND, 228)

    def testPercentile(self):
        self.assertAlmostEqual(self._level.percentile(), -11.427970426543833)

    def testPercentileFirstSlice(self):
        slices = self._level.slice()
