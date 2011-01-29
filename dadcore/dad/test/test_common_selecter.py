# -*- Mode: Python; test-case-name: dad.test.test_common_selecter -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import math

import unittest

from twisted.internet import defer

from dad.audio import mixing
from dad.common import selecter

class EmptyTest(unittest.TestCase):

    def setUp(self):
        self._selecter = selecter.SimplePlaylistSelecter(None)

    def testGet(self):
        self.failIf(self._selecter.getNow())

class SimpleTest(unittest.TestCase):

    def setUp(self):
        tm1 = mixing.TrackMix()        
        tm1.start = 5.0
        tm2 = mixing.TrackMix()        
        tm2.start = 10.0
        tm3 = mixing.TrackMix()        
        tm3.start = 15.0
        self._tracks = {
            '/path/one.ogg': [tm1, ],
            '/path/two.ogg': [tm2, ],
            '/path/three.ogg': [tm3, ],
            }
        self._selecter = selecter.SimplePlaylistSelecter(None)
        self._selecter._tracks = self._tracks

    def testGet(self):
        d = defer.Deferred()

        # assure we get all three tracks in a row, every time
        for loop in range(5):

            result = []
            for i in range(3):
                d.addCallback(lambda _: self._selecter.get())
                d.addCallback(lambda r: result.append(r))

            def checkCb(_):
                for path, tm in result:
                    self.failUnless(path in self._tracks.keys())
                    self.assertEquals(self._tracks[path][0], tm)


            d.addCallback(checkCb)

        # trigger
        d.callback(None)
