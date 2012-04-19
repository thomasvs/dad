# -*- Mode: Python; test-case-name: dad.test.test_memorydb_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import os
import tempfile

from twisted.internet import defer

from dad.plugins import pdad
from dad.memorydb import memory

from dad.test import mixin_database

from dad.test import common # logging


class MemoryDBTestCase(mixin_database.BaseTestCase, unittest.TestCase):
    """
    I am a base class for mixin_database tests using the memory database.
    """

    def setUp(self):
        self.testdb = memory.MemoryDB()
        self.provider = pdad.CoreDatabaseProvider()

class MemoryDBPickleTestCase(mixin_database.BaseTestCase):
    """
    I am a base class for mixin_database tests using the memory database
    with pickle storage.
    """

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=u'.dad.test.memorydb')
        os.close(self._fd)

        self.testdb = memory.MemoryDB(self._path)
        self.provider = pdad.CoreDatabaseProvider()

    def tearDown(self):
        os.unlink(self._path)

# instantiate all generic database tests
globals().update(mixin_database.makeTestCaseClasses(MemoryDBTestCase))

# additional tests
class MemoryDatabasePickleTestCase(MemoryDBPickleTestCase, unittest.TestCase):

    @defer.inlineCallbacks
    def testScorePersists(self):
        t = self.testdb.new('track', name=u'Crap Song')
        yield self.testdb.save(t)

        yield self.testdb.score(t, u'thomas', u'Good', 0.1)
        yield self.testdb.score(t, u'thomas', u'Party', 0.2)

        # now get a new database
        testdb = memory.MemoryDB(self._path)
        categories = yield testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)
