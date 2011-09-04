# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import os
import tempfile

from twisted.internet import defer

from dad.plugins import pdad
from dad.database import memory

from dad.test import test_database


class MemoryDBTestCase(test_database.BaseTestCase):
    """
    I am a base class for test_database tests using the memory database.
    """

    def setUp(self):
        self.testdb = memory.MemoryDB()
        self.provider = pdad.CoreDatabaseProvider()

class MemoryDBPickleTestCase(test_database.BaseTestCase):
    """
    I am a base class for test_database tests using the memory database
    with pickle storage.
    """

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=u'.dad.test.memorydb')
        os.close(self._fd)

        self.testdb = memory.MemoryDB(self._path)
        self.provider = pdad.CoreDatabaseProvider()

    def tearDown(self):
        os.unlink(self._path)

# subclass all test_database tests

class MemoryTrackModelTestCase(test_database.TrackModelTest, MemoryDBTestCase):
    pass
class MemoryTrackSelectorModelTestCase(test_database.TrackSelectorModelTest,
    MemoryDBTestCase):
    pass
class MemoryArtistSelectorModelTestCase(test_database.ArtistSelectorModelTest,
    MemoryDBTestCase):
    pass
class MemoryDatabaseTestCase(test_database.DatabaseTestCase,
    MemoryDBTestCase):
    pass

# additional tests
class MemoryDatabasePickleTestCase(MemoryDBPickleTestCase):

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
