# -*- Mode: Python; test-case-name: dadcouch.test.test_controller -*-
# vi:si:et:sw=4:sts=4:ts=4

#__metaclass__ = type

import os
import commands

from twisted.internet import defer

from dad.plugins import pdadcouch

from dadcouch.extern.paisley.test import test_util

from dadcouch.model import daddb

from dad.test import mixin_controller

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


class CouchDatabaseTestCase(mixin_controller.BaseTestCase, DADDBTestCase):
    """
    I am a base class for tests defined in mixin_controller.
    """

    @defer.inlineCallbacks
    def setUp(self):
        yield DADDBTestCase.setUp(self)
        self.provider = pdadcouch.CouchDBDatabaseProvider()

# instantiate all generic database tests
globals().update(mixin_controller.makeTestCaseClasses(CouchDatabaseTestCase))
