# -*- Mode: Python; test_case_name: dadcouch.test.test_model_artist -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dadcouch.database import mappings
from dadcouch.model import artist

from dadcouch.test import test_model_daddb

class ArtistModelTestCase(test_model_daddb.DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = artist.ArtistModel(self.daddb)

        mapping = mappings.Artist(name=u'The Afghan Whigs')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', mapping._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            mappings.Artist)
        self.assertEquals(retrieved.name, u'The Afghan Whigs')

        retrieved = yield model.get(stored['id'])
        name = yield retrieved.getName()
        self.assertEquals(name, u'The Afghan Whigs')

    @defer.inlineCallbacks
    def test_score(self):

        model = artist.ArtistModel(self.daddb)

        mapping = mappings.Artist(name=u'The Afghan Whigs')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', mapping._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            mappings.Artist)
        # FIXME: cheat here
        model.artist = retrieved

        scored = yield model.score(model, u'thomas', u'Good', 0.7)

        scores = yield scored.getScores()
        scores = list(scores)
        self.assertEquals(len(scores), 1)
        self.assertEquals(scores[0].user, 'thomas')
        self.assertEquals(scores[0].category, 'Good')
        self.assertEquals(scores[0].score, 0.7)

class ArtistSelectorModelTestCase(test_model_daddb.DADDBTestCase):

    @defer.inlineCallbacks
    def test_get(self):

        model = artist.ArtistSelectorModel(self.daddb)

        mapping = mappings.Artist(name=u'The Afghan Whigs')
        # FIXME: don't poke at _data
        stored = yield self.db.saveDoc('dadtest', mapping._data)

        retrieved = yield self.daddb.db.map(self.daddb.dbName, stored['id'],
            mappings.Artist)
        self.assertEquals(retrieved.name, u'The Afghan Whigs')

        # we need a track for this artist to show up

        mapping = mappings.Track(name=u'Milez iz Dead', artists=[{
            'name': u'The Afghan Whigs',
            'id': stored['id'],
        }])
        trackStored = yield self.db.saveDoc('dadtest', mapping._data)

        retrieved = yield model.get()
        retrieved = list(retrieved)

        name = yield retrieved[0].getName()
        self.assertEquals(name, u'The Afghan Whigs')
        mid = yield retrieved[0].getMid()
        self.assertEquals(mid, stored['id'])
