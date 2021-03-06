# -*- Mode: Python; test-case-name: dadcouch.test.test_database_internal -*-
# vi:si:et:sw=4:sts=4:ts=4

#__metaclass__ = type

from twisted.internet import defer

from dad.logic import database

from dadcouch.database import mappings, internal
from dadcouch.model import track as mtrack

from dadcouch.test import test_database_couch


# FIXME: test Internal directly

class SimpleTestCase(test_database_couch.DADDBTestCase):

    @defer.inlineCallbacks
    def test_addTrackSimple(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'

        track = mappings.Track(
            name='Hit Me',
            fragments=[
                {
                    'files': [{
                        'host': host,
                        'path': path,
                    }],
                }]
        )

        stored = yield self.daddb._internal.saveDoc(track)

        # look up
        ret = yield self.daddb._internal.getTracksByHostPath(host, path)

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

        track = mappings.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb._internal.saveDoc(track)


        # look up
        ret = yield self.daddb._internal.viewDocs('view-host-path', internal.GenericRow)

        results = list(ret)
        self.assertEquals(len(results), 1)
        self.assertEquals(results[0].key[0], host)
        self.assertEquals(results[0].key[1], path)

    @defer.inlineCallbacks
    def test_addTrackCompositeMultiHost(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'
        info = database.FileInfo(host=host, path=path)

        track = mappings.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb._internal.saveDoc(track)

        info = database.FileInfo(host=host + '-2', path=path)
        track = mappings.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb._internal.saveDoc(track)


        # look up
        ret = yield self.daddb._internal.getTracksByHostPath(host, path)

        results = list(ret)
        self.assertEquals(len(results), 1)

        track = results[0]
        fragment = track.fragments[0]
        file = fragment.files[0]
        self.assertEquals(file.host, host)
        self.assertEquals(file.path, path)


class MD5TestCase(test_database_couch.DADDBTestCase):
    @defer.inlineCallbacks
    def test_addSameSumDifferentHost(self):
        host = u'localhost'
        path = u'/tmp/hitme.flac'
        md5sum = u'deadbeef'

        info = database.FileInfo(host=host, path=path, md5sum=md5sum)

        # add track
        track = mappings.Track(name='Hit Me')
        track.addFragment(info)

        stored = yield self.daddb._internal.save(track)

        # add a fragment to it for same file on different host
        info = database.FileInfo(host=host + '-2', path=path, md5sum=md5sum)

        yield self.daddb._internal.trackAddFragmentFileByMD5Sum(stored, info)

        # look up track through first fragment file
        ret = yield self.daddb._internal.getTracksByHostPath(host, path)

        results = list(ret)
        self.assertEquals(len(results), 1)

        track = results[0]
        fragment = track.fragments[0]
        file = fragment.files[0]
        self.assertEquals(file.host, host)
        self.assertEquals(file.path, path)
        self.assertEquals(file.md5sum, md5sum)


        # look up second and make sure the id is the same
        ret = yield self.daddb._internal.getTracksByHostPath(host + '-2', path)
        results = list(ret)

        self.assertEquals(len(results), 1)
        self.assertEquals(results[0].id, stored.id)

        # add a third one 

        ret = yield self.daddb._internal.getTracksByHostPath(host, path)
        info = database.FileInfo(host=host + '-3', path=path, md5sum=md5sum)
        yield self.daddb._internal.trackAddFragmentFileByMD5Sum(stored, info)

        # look up third and make sure the id is the same
        ret = yield self.daddb._internal.getTracksByHostPath(host + '-3', path)
        results = list(ret)

        self.assertEquals(len(results), 1)
        self.assertEquals(results[0].id, stored.id)

          
class OldSimpleTestCase: # old test cases (test_database_couch.DADDBTestCase):

    @defer.inlineCallbacks
    def test_getCategory(self):
        category = mappings.Category(name='Good')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', category._data)
        retrieved = yield self.daddb._internal.getCategory('Good')

        for key in [u'name', u'type']:
            self.assertEquals(category[key], retrieved[key])
        for key in [u'id', u'rev']:
            self.assertEquals(stored[key], retrieved[u'_' + key])

        categories = yield self.daddb._internal.getCategories()
        categories = list(categories)
        self.assertEquals(categories[0].name, u'Good')

    @defer.inlineCallbacks
    def test_getOrAddUser(self):
        # first one adds
        retrieved = yield self.daddb._internal.getOrAddUser('thomas')

        self.assertEquals(retrieved[u'name'], 'thomas')
        self.assertEquals(type(retrieved[u'name']), unicode)

        # second one only retrieves
        retrieved = yield self.daddb._internal.getOrAddUser('thomas')

        self.assertEquals(retrieved[u'name'], 'thomas')
        self.assertEquals(type(retrieved[u'name']), unicode)

        # try one with unicode
        name = u'j\xe9r\xe9my'
        retrieved = yield self.daddb._internal.getOrAddUser(name)

        self.assertEquals(retrieved[u'name'], name)
        self.assertEquals(type(retrieved[u'name']), unicode)


class AdvancedTestCase:#(test_database_couch.DADDBTestCase):

    @defer.inlineCallbacks
    def setUp(self):
        yield DADDBTestCase.setUp(self)

        objs = []
        self.ids = []

        objs.append(mappings.Category(name='Good'))
        objs.append(mappings.User(name='thomas'))
        objs.append(mappings.Track(name='hit me with your rhythm stick'))

        for o in objs:
            ret = yield self.db.saveDoc('dadtest', o._data)
            self.ids.append(ret['id'])

    @defer.inlineCallbacks
    def test_score(self):
        track = yield self.db.map('dadtest', self.ids[2], mappings.Track)
        ret = yield self.daddb._internal.score(track, 'thomas', 'Good', 0.7)

        # we should have only one track
        category = yield self.db.map('dadtest', self.ids[0], mappings.Category)
        trackScores = yield self.daddb._internal.getTrackScoresByCategory(category)
        trackScores = list(trackScores)
        self.assertEquals(len(trackScores), 1)
        ts = trackScores[0]
        self.assertEquals(ts.categoryId, category.id)
        self.assertEquals(ts.score, 0.7)

        # this should be the only random track
        t = yield self.daddb._internal.getTrack('thomas', 'Good', 0.6, 0.8)
        (random, s, userId) = t
        self.assertEquals(random.name, track.name)
        self.assertEquals(s, 0.7)
        self.assertEquals(userId, self.ids[1])

        scores = yield self.daddb._internal.getScores(track)
        scores = list(scores)
        
        self.assertEquals(scores[0].subject_type, 'track')
        self.assertEquals(scores[0].subject_id, track.id)

        # test track model
        model = mtrack.TrackModel(self.daddb._internal)

        retrieved = yield model.get(track.id)
        res = yield model.getScores()

        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].user_id, userId)


class TrackModelTestCase:#(test_database_couch.DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = mtrack.TrackModel(self.daddb._internal)

        track = mappings.Track(name='hit me')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', track._data)

        retrieved = yield self.daddb._internal.db.map(self.daddb._internal.dbName, stored['id'],
            mappings.Track)
        self.assertEquals(retrieved.name, 'hit me')

        retrieved = yield model.get(stored['id'])
        self.assertEquals(retrieved.name, 'hit me')
