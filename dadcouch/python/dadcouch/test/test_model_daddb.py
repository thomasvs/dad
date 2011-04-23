# -*- Mode: Python; test_case_name: dadcouch.test.test_model_daddb -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import commands

from twisted.internet import defer
from twisted.trial import unittest

from dadcouch.extern.paisley.test import test_util

from dadcouch.model import daddb, couch


class CategoryTestCase(test_util.CouchDBTestCase):
    @defer.inlineCallbacks
    def setUp(self):
        test_util.CouchDBTestCase.setUp(self)

        # set up database

        yield self.db.createDB('dadtest')

        self.daddb = daddb.DADDB(self.db, 'dadtest')

        thisDir = os.path.dirname(__file__)
        couchPath = os.path.abspath(
            os.path.join(thisDir, '..', '..', '..', 'couchdb'))
        (status, output) = commands.getstatusoutput(
            "couchapp push --docid _design/dad " + \
            "%s http://localhost:%d/dadtest/" % (couchPath, self.wrapper.port))
        self.failIf(status, "Could not execute couchapp: %s" % output)

    @defer.inlineCallbacks
    def test_getCategory(self):
        category = couch.Category(name='Good')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', category._data)
        retrieved = yield self.daddb.getCategory('Good')

        for key in [u'name', u'type']:
            self.assertEquals(category[key], retrieved[key])
        for key in [u'id', u'rev']:
            self.assertEquals(stored[key], retrieved[u'_' + key])

    @defer.inlineCallbacks
    def test_getOrAddUser(self):
        retrieved = yield self.daddb.getOrAddUser('thomas')

        self.assertEquals(retrieved[u'name'], 'thomas')
        self.assertEquals(type(retrieved[u'name']), unicode)

        name = u'j\xe9r\xe9my'
        retrieved = yield self.daddb.getOrAddUser(name)

        self.assertEquals(retrieved[u'name'], name)
        self.assertEquals(type(retrieved[u'name']), unicode)

