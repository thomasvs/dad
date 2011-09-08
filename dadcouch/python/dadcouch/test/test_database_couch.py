# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

#__metaclass__ = type

import os
import commands

from twisted.internet import defer

from dad.logic import database

from dad.plugins import pdadcouch

from dadcouch.extern.paisley.test import test_util

from dadcouch.model import daddb, couch
from dadcouch.model import track as mtrack

from dad.test import test_database

class DADDBTestCase(test_util.CouchDBTestCase):

    """
    @type db:    L{paisley.client.CouchDB}
    @type daddb: L{daddb.DADDB}
    """

    @defer.inlineCallbacks
    def setUp(self):
        test_util.CouchDBTestCase.setUp(self)

        # set up database

        yield self.db.createDB('dadtest')

        self.daddb = daddb.DADDB(self.db, 'dadtest')
        self.testdb = self.daddb

        thisDir = os.path.dirname(__file__)
        couchPath = os.path.abspath(
            os.path.join(thisDir, '..', '..', '..', 'couchdb'))
        (status, output) = commands.getstatusoutput(
            "couchapp push --docid _design/dad " + \
            "%s http://localhost:%d/dadtest/" % (couchPath, self.wrapper.port))
        self.failIf(status, "Could not execute couchapp: %s" % output)


class CouchDatabaseTestCase(test_database.BaseTestCase, DADDBTestCase):
    """
    I am a base class for tests defined in test_database.
    """

    @defer.inlineCallbacks
    def setUp(self):
        yield DADDBTestCase.setUp(self)
        self.provider = pdadcouch.CouchDBDatabaseProvider()

# instantiate all generic database tests
globals().update(test_database.makeTestCaseClasses(CouchDatabaseTestCase))
