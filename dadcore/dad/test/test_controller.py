# -*- Mode: Python; test-case-name: dad.test.test_controller -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import os
import tempfile

from dad.plugins import pdad
from dad.memorydb import memory

from dad.test import mixin_controller


class MemoryDBTestCase(mixin_controller.BaseTestCase, unittest.TestCase):
    """
    I am a base class for mixin_controller tests using the memory database.
    """

    def setUp(self):
        self.testdb = memory.MemoryDB()
        self.provider = pdad.CoreDatabaseProvider()

class MemoryDBPickleTestCase(mixin_controller.BaseTestCase):
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
globals().update(mixin_controller.makeTestCaseClasses(MemoryDBTestCase))
