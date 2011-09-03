# -*- Mode: Python; test_case_name: dadcouch.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dadcouch.model import couch
from dadcouch.model import track as mtrack

from dadcouch.test import test_model_daddb


class TrackModelTestCase(test_model_daddb.DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = mtrack.TrackModel(self.daddb)

        track = couch.Track(name='hit me')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', track._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            couch.Track)
        self.assertEquals(retrieved.name, 'hit me')

        retrieved = yield model.get(stored['id'])
        name = yield retrieved.getName()
        self.assertEquals(name, 'hit me')

    @defer.inlineCallbacks
    def test_score(self):

        model = mtrack.TrackModel(self.daddb)

        track = couch.Track(name='hit me')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', track._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            couch.Track)
        # FIXME: cheat here
        model.track = retrieved

        scored = yield model.score(model, u'thomas', u'Good', 0.7)

        scores = yield scored.getScores()
        scores = list(scores)
        self.assertEquals(len(scores), 1)
        self.assertEquals(scores[0].user, 'thomas')
        self.assertEquals(scores[0].category, 'Good')
        self.assertEquals(scores[0].score, 0.7)

class TrackSelectorModelTestCase(test_model_daddb.DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = mtrack.TrackSelectorModel(self.daddb)

        track = couch.Track(name='hit me')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', track._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            couch.Track)
        self.assertEquals(retrieved.name, 'hit me')

        retrieved = yield model.get()
        retrieved = list(retrieved)

        name = yield retrieved[0].getName()
        self.assertEquals(name, 'hit me')
