# -*- Mode: Python; test_case_name: dadcouch.test.test_common_manydef -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.trial import unittest

from dadcouch.common import manydef

class DeferredListSpacedTestCase(unittest.TestCase):

    # FIXME: add test for a broken listcount function
    # a deferred-returning callback to test with
    def listcount(self, res, count):
        count.append(res)

        d = defer.Deferred()
        d.callback(None)
        return d

    def test_DLS(self):

        d = manydef.DeferredListSpaced()

        count = []
        for i in range(0, 1000):
            d.addCallable(self.listcount, i, count)

        d.start()

        def check(_):
            self.assertEquals(len(count), 1000)
        d.addCallback(check)
        return d

