# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import os
import tempfile

from twisted.internet import defer

from dad.database import memory

# extract to separate module as base class for all database tests
class DBTest:
    """
    @ivar testdb: the database being tested
    """

    @defer.inlineCallbacks
    def testNewSave(self):
        t = yield self.testdb.new()
        yield self.testdb.save(t)

    @defer.inlineCallbacks
    def testScore(self):
        t = self.testdb.new()
        yield self.testdb.save(t)

        yield self.testdb.score(t, u'thomas', u'Good', 0.1)
        yield self.testdb.score(t, u'thomas', u'Party', 0.2)

        categories = yield self.testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)

class MemoryDBDatabaseTest(DBTest, unittest.TestCase):

    def setUp(self):
        self.testdb = memory.MemoryDB()

class MemoryDBPickleDatabaseTest(DBTest, unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=u'.dad.test.memorydb')
        os.close(self._fd)
        self.testdb = memory.MemoryDB(self._path)

    def tearDown(self):
        os.unlink(self._path)

class MemoryDBPickleTest(DBTest, unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=u'.dad.test.memorydb')
        os.close(self._fd)
        self.testdb = memory.MemoryDB(self._path)

    @defer.inlineCallbacks
    def testScore(self):
        t = self.testdb.new()
        yield self.testdb.save(t)

        yield self.testdb.score(t, u'thomas', u'Good', 0.1)
        yield self.testdb.score(t, u'thomas', u'Party', 0.2)

        # now get a new database
        testdb = memory.MemoryDB(self._path)
        categories = yield testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)


    def tearDown(self):
        os.unlink(self._path)


