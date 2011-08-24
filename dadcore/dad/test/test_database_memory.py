# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import os
import tempfile

from twisted.internet import defer

from dad.plugins import pdad
from dad.logic import database
from dad.database import memory
from dad.test import common

# extract to separate module as base class for all database tests
class DBTest:
    """
    Subclass me to have database-specific tests run against the generic
    tests.

    The subclass is responsible for settings testdb.

    @ivar testdb:   the database being tested
    @type testdb:   an implementer of L{idad.IDatabase}
    @ivar provider: the database provider
    @type provider: an implementor of L{idad.IDatabaseProvider}
    """

    @defer.inlineCallbacks
    def testNewSave(self):
        t = yield self.testdb.new()
        yield self.testdb.save(t)

    @defer.inlineCallbacks
    def testScore(self):
        t = self.testdb.new()

        # make sure it gets an id
        t = yield self.testdb.save(t)

        t = yield self.testdb.score(t, u'thomas', u'Good', 0.1)
        t = yield self.testdb.score(t, u'thomas', u'Party', 0.2)

        categories = yield self.testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)

        scores = yield self.testdb.getScores(t)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.1)

        # update score
        yield self.testdb.score(t, u'thomas', u'Good', 0.3)

        scores = yield self.testdb.getScores(t)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.3)

    @defer.inlineCallbacks
    def testFragments(self):
        t = self.testdb.new()
        yield self.testdb.save(t)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()

        t.addFragment(info, metadata=metadata)
        yield self.testdb.save(t)

    @defer.inlineCallbacks
    def testArtistSelectorModel(self):
        appModel = self.provider.getAppModel(self.testdb)
        asModel = appModel.getModel('ArtistSelector')

        t = self.testdb.new()
        yield self.testdb.save(t)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'

        t.addFragment(info, metadata=metadata)
        yield self.testdb.save(t)
        
        artists = yield asModel.get()
        self.assertEquals(len(artists), 1)
        self.assertEquals(artists[0].getName(), u'The Afghan Whigs')
        

class MemoryDBDatabaseTest(DBTest, unittest.TestCase):

    def setUp(self):
        self.testdb = memory.MemoryDB()
        self.provider = pdad.CoreDatabaseProvider()

class MemoryDBPickleDatabaseTest(DBTest, unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=u'.dad.test.memorydb')
        os.close(self._fd)

        self.testdb = memory.MemoryDB(self._path)
        self.provider = pdad.CoreDatabaseProvider()

    def tearDown(self):
        os.unlink(self._path)

class MemoryDBPickleTest(MemoryDBPickleDatabaseTest):

    @defer.inlineCallbacks
    def testScorePersists(self):
        t = self.testdb.new()
        yield self.testdb.save(t)

        yield self.testdb.score(t, u'thomas', u'Good', 0.1)
        yield self.testdb.score(t, u'thomas', u'Party', 0.2)

        # now get a new database
        testdb = memory.MemoryDB(self._path)
        categories = yield testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)
