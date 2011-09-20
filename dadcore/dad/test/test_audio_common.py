# -*- Mode: Python; test-case-name: dad.test.test_audio_common -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

from dad.audio import common

class ExtremeTest(unittest.TestCase):
    def testZero(self):
        self.assertEquals(common.rawToDecibel(0.0), -1000.0)

    # FIXME: cannot get OverflowError
    def noTestOverflow(self):
        self.assertRaises(OverflowError, common.rawToDecibel, 0.0)
