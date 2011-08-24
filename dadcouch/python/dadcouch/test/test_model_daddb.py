# -*- Mode: Python; test_case_name: dadcouch.test.test_model_daddb -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import commands

from twisted.internet import defer

from dad.logic import database

from dad.test import test_database_memory

from dad.plugins import pdadcouch

from dadcouch.extern.paisley import mapping
from dadcouch.extern.paisley.test import test_util

from dadcouch.model import daddb, couch


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


class DADDBTest(test_database_memory.DBTest, DADDBTestCase):

    @defer.inlineCallbacks
    def setUp(self):
        yield DADDBTestCase.setUp(self)
        self.provider = pdadcouch.CouchDBDatabaseProvider()



class SimpleTestCase(DADDBTestCase):

    @defer.inlineCallbacks
    def test_addTrackSimple(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'

        track = couch.Track(
            name='Hit Me',
            fragments=[
                {
                    'files': [{
                        'host': host,
                        'path': path,
                    }],
                }]
        )

        stored = yield self.daddb.saveDoc(track)

        # look up
        ret = yield self.daddb.getTrackByHostPath(host, path)

        results = list(ret)
        self.assertEquals(len(results), 1)

        track = results[0]
        fragment = track.fragments[0]
        file = fragment.files[0]
        self.assertEquals(file.host, host)
        self.assertEquals(file.path, path)

    @defer.inlineCallbacks
    def test_addTrackComposite(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'
        info = database.FileInfo(host=host, path=path)

        track = couch.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb.saveDoc(track)


        # look up
        ret = yield self.daddb.viewDocs('view-host-path', daddb.GenericRow)

        results = list(ret)
        self.assertEquals(len(results), 1)
        self.assertEquals(results[0].key[0], host)
        self.assertEquals(results[0].key[1], path)

    @defer.inlineCallbacks
    def test_addTrackCompositeMultiHost(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'
        info = database.FileInfo(host=host, path=path)

        track = couch.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb.saveDoc(track)

        info = database.FileInfo(host=host + '-2', path=path)
        track = couch.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb.saveDoc(track)


        # look up
        ret = yield self.daddb.getTrackByHostPath(host, path)

        results = list(ret)
        self.assertEquals(len(results), 1)

        track = results[0]
        fragment = track.fragments[0]
        file = fragment.files[0]
        self.assertEquals(file.host, host)
        self.assertEquals(file.path, path)


class MD5TestCase(DADDBTestCase):
    @defer.inlineCallbacks
    def test_addSameSumDifferentHost(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'
        md5sum = u'deadbeef'

        info = database.FileInfo(host=host, path=path, md5sum=md5sum)

        # add track
        track = couch.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb.save(track)

        # add a fragment to it for same file on different host
        info = database.FileInfo(host=host + '-2', path=path, md5sum=md5sum)

        yield self.daddb.trackAddFragmentFileByMD5Sum(stored, info)

        # look up track through first fragment file
        ret = yield self.daddb.getTrackByHostPath(host, path)

        results = list(ret)
        self.assertEquals(len(results), 1)

        track = results[0]
        fragment = track.fragments[0]
        file = fragment.files[0]
        self.assertEquals(file.host, host)
        self.assertEquals(file.path, path)
        self.assertEquals(file.md5sum, md5sum)


        # look up second and make sure the id is the same
        ret = yield self.daddb.getTrackByHostPath(host + '-2', path)
        results = list(ret)

        self.assertEquals(len(results), 1)
        self.assertEquals(results[0].id, stored.id)

        # add a third one 

        ret = yield self.daddb.getTrackByHostPath(host, path)
        info = database.FileInfo(host=host + '-3', path=path, md5sum=md5sum)
        yield self.daddb.trackAddFragmentFileByMD5Sum(stored, info)

        # look up third and make sure the id is the same
        ret = yield self.daddb.getTrackByHostPath(host + '-3', path)
        results = list(ret)

        self.assertEquals(len(results), 1)
        self.assertEquals(results[0].id, stored.id)

          
class OldSimpleTestCase: # old test cases (DADDBTestCase):

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

        categories = yield self.daddb.getCategories()
        categories = list(categories)
        self.assertEquals(categories[0].name, u'Good')

    @defer.inlineCallbacks
    def test_getOrAddUser(self):
        # first one adds
        retrieved = yield self.daddb.getOrAddUser('thomas')

        self.assertEquals(retrieved[u'name'], 'thomas')
        self.assertEquals(type(retrieved[u'name']), unicode)

        # second one only retrieves
        retrieved = yield self.daddb.getOrAddUser('thomas')

        self.assertEquals(retrieved[u'name'], 'thomas')
        self.assertEquals(type(retrieved[u'name']), unicode)

        # try one with unicode
        name = u'j\xe9r\xe9my'
        retrieved = yield self.daddb.getOrAddUser(name)

        self.assertEquals(retrieved[u'name'], name)
        self.assertEquals(type(retrieved[u'name']), unicode)


class AdvancedTestCase:#(DADDBTestCase):

    @defer.inlineCallbacks
    def setUp(self):
        yield DADDBTestCase.setUp(self)

        objs = []
        self.ids = []

        objs.append(couch.Category(name='Good'))
        objs.append(couch.User(name='thomas'))
        objs.append(couch.Track(name='hit me with your rhythm stick'))

        for o in objs:
            ret = yield self.db.saveDoc('dadtest', o._data)
            self.ids.append(ret['id'])

    @defer.inlineCallbacks
    def test_score(self):
        track = yield self.db.map('dadtest', self.ids[2], couch.Track)
        ret = yield self.daddb.score(track, 'thomas', 'Good', 0.7)

        # we should have only one track
        category = yield self.db.map('dadtest', self.ids[0], couch.Category)
        trackScores = yield self.daddb.getTrackScoresByCategory(category)
        trackScores = list(trackScores)
        self.assertEquals(len(trackScores), 1)
        ts = trackScores[0]
        self.assertEquals(ts.categoryId, category.id)
        self.assertEquals(ts.score, 0.7)

        # this should be the only random track
        t = yield self.daddb.getTrack('thomas', 'Good', 0.6, 0.8)
        (random, s, userId) = t
        self.assertEquals(random.name, track.name)
        self.assertEquals(s, 0.7)
        self.assertEquals(userId, self.ids[1])

        scores = yield self.daddb.getScores(track)
        scores = list(scores)
        
        self.assertEquals(scores[0].subject_type, 'track')
        self.assertEquals(scores[0].subject_id, track.id)

        # test track model
        model = daddb.TrackModel(self.daddb)

        retrieved = yield model.get(track.id)
        res = yield model.getScores()

        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].user_id, userId)


class TrackSelectorModelTestCase:#(DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = daddb.TrackSelectorModel(self.daddb)

        artist = couch.Artist(name='ian dury')
        stored = yield self.db.saveDoc('dadtest', artist._data)
        artistId = stored['id']

        track = couch.Track(name='hit me', artist_ids=[artistId, ])

        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', track._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            couch.Track)
        self.assertEquals(retrieved.name, 'hit me')

        def cb(res):
            self.cbCalled = True
            self.assertEquals(res.name, 'hit me')

        self.cbCalled = False
        got = yield model.get(cb=cb)
        self.failUnless(self.cbCalled)

        # self.assertEquals(type(retrieved), generator)

        first = got[0]
        artist = yield self.db.map(self.daddb.dbName, artistId, couch.Artist)
        self.assertEquals(first.name, 'hit me')

        # can't compare two mapped objects directly
        self.assertEquals(first.artists[0].name, artist.name)

class TrackModelTestCase:#(DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = daddb.TrackModel(self.daddb)

        track = couch.Track(name='hit me')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', track._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            couch.Track)
        self.assertEquals(retrieved.name, 'hit me')

        retrieved = yield model.get(stored['id'])
        self.assertEquals(retrieved.name, 'hit me')
