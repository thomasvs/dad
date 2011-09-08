# -*- Mode: Python; test-case-name: dadcouch.test.test_common_manydef -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.trial import unittest

from dadcouch.common import manydef

class DLSTestCase(unittest.TestCase):

    def setUp(self):
        self.count = []
        self.failures = []

    # FIXME: add test for a broken listcount function
    # a deferred-returning callback to test with
    def listcount(self, res, count):
        count.append(res)

        d = defer.Deferred()
        d.callback(None)
        return d

    def listcounterror(self, res, count):
        str(u'\xe0')

    def listcountCallback(self, _, res, count):
        count.append(res)

    def listcountErrback(self, _, res, count):
        self.assertEquals(count, self.failures)
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

    def DLSErrbacks(self, count):

        # without consumeErrors, this test ERROR's.
        dls = manydef.DeferredListSpaced(consumeErrors=1)

        for i in range(0, count):
            dls.addCallable(self.listcounterror, i, self.count)
            dls.addCallableErrback(self.listcountErrback, i, self.failures)

        def check(_):
            self.assertEquals(len(self.count), 0)
            self.assertEquals(len(self.failures), count)

        dls.addCallback(check)
        dls.start()
        return dls

    def test_DLSErrbackOne(self):
        return self.DLSErrbacks(1)

    def test_DLSErrbackSpaceMinus(self):
        return self.DLSErrbacks(manydef.DeferredListSpaced.SPACE - 1)

    def test_DLSErrbackSpace(self):
        return self.DLSErrbacks(manydef.DeferredListSpaced.SPACE)

    def test_DLSErrbackSpacePlus(self):
        return self.DLSErrbacks(manydef.DeferredListSpaced.SPACE + 1)

    def test_DLSErrbackSpaceTwice(self):
        return self.DLSErrbacks(manydef.DeferredListSpaced.SPACE * 2)

