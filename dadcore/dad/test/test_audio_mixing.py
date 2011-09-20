# -*- Mode: Python; test-case-name: dad.test.test_audio_mixing -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import pickle
import exceptions

import unittest

from dad.audio import mixing
from dad.audio import level as mlevel


class SimpleTest(unittest.TestCase):

    def testTrackMix(self):
        tm = mixing.TrackMix()        
        tm.rmsPercentile = -9.0
        tm.peak = -3.0
        tm.start = 5.0

        # We need to drop -6 dB from -9.0 to reach -15.0
        self.assertEquals(tm.getVolume(), -6.0)

        # We can go up and distort too
        self.assertEquals(tm.getVolume(rmsTarget=-3.0), 3.0)

    def testFromLevels(self):
        handle = open(os.path.join(os.path.dirname(__file__), 'home.pickle'))
        level = pickle.load(handle)
        tm = mixing.fromLevels(level, level)

        level2 = level.convert(mlevel.SCALE_RAW)
        del level2[-1]
        self.assertRaises(exceptions.AssertionError,
            mixing.fromLevels, level, level2)

        level2 = level.convert(mlevel.SCALE_RAW)
        # FIXME: pokey
        level2._start = level2[0][0]
        self.assertRaises(exceptions.AssertionError,
            mixing.fromLevels, level, level2)

    def testMix(self):
        tm1 = mixing.TrackMix()        
        tm1.rmsPercentile = -9.0
        tm1.peak = -3.0
        tm1.start = 5.0
        tm1.end = 180.0

        tm2 = mixing.TrackMix()        
        tm2.rmsPercentile = -8.0
        tm2.peak = -4.0
        tm2.start = 10.0
        tm2.end = 170.0

        mix = mixing.Mix(tm1, tm2)
        self.assertEquals(mix.volume1, -6.0)
        self.assertEquals(mix.volume2, -7.0)


    def testMixWithAttackDecay(self):
        handle = open(os.path.join(os.path.dirname(__file__), 'home.pickle'))
        level = pickle.load(handle)

        tm1 = mixing.TrackMix()        
        tm1.rmsPercentile = -9.0
        tm1.peak = -3.0
        tm1.start = 5.0
        tm1.end = 180.0
        tm1.attack = level.attack()
        tm1.decay = level.decay()

        tm2 = mixing.TrackMix()        
        tm2.rmsPercentile = -8.0
        tm2.peak = -4.0
        tm2.start = 10.0
        tm2.end = 170.0
        tm2.attack = level.decay()
        tm2.decay = level.attack()


        mix = mixing.Mix(tm1, tm2)
        self.assertEquals(mix.volume1, -6.0)
        self.assertEquals(mix.volume2, -7.0)



