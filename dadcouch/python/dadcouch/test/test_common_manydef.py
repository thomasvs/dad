# -*- Mode: Python; test_case_name: dadcouch.test.test_common_manydef -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.trial import unittest

from dadcouch.common import manydef

class DeferredListSpacedTestCase(unittest.TestCase):

    def setUp(self):
        self.count = []

    # FIXME: add test for a broken listcount function
    # a deferred-returning callback to test with
    def listcount(self, res, count):
        count.append(res)

        d = defer.Deferred()
        d.callback(None)
        return d

    def listcountCallback(self, _, res, count):
        count.append(res)

    def dlscount(self, dls, check, withCb=False):

        for i in range(0, 1000):
            dls.addCallable(self.listcount, i, self.count)
            if withCb:
                dls.addCallableCallback(self.listcountCallback, i, self.count)

        dls.start()
        dls.addCallback(check)
        return dls


    def test_DLS(self):

        dls = manydef.DeferredListSpaced()

        def check(_):
            self.assertEquals(len(self.count), 1000)

        return self.dlscount(dls, check)

    def test_DLSOne(self):

        dls = manydef.DeferredListSpaced(fireOnOneCallback=True)

        def check(_):
            self.assertEquals(len(self.count), 1)
        return self.dlscount(dls, check)

    def test_DLSCallback(self):

        dls = manydef.DeferredListSpaced()

        def check(_):
            self.assertEquals(len(self.count), 2000)

        return self.dlscount(dls, check, withCb=True)
