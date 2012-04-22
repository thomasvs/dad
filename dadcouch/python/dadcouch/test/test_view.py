# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

from dadcouch.extern.paisley import pjson

from dadcouch.extern.paisley.test import util

from dadcouch.database import mappings


class CouchViewServerTestCase(util.CouchQSTestCase):
    """
    I am a base class for tests.
    """
    QueryServerClass = util.CouchJSWrapper
    path = os.path.abspath(os.path.join(os.path.dirname(__file__),
        '..', '..', '..', 'couchdb'))

    def setUp(self):
        util.CouchQSTestCase.setUp(self)
        self.wrapper.path = self.path

    def test_view_mbtrackid(self):
        track = mappings.Track(name=u'track')
        track.fragments = [
            {
                'files': [],
                'chroma': {
                    'chromaprint': None,
                    'mbid': 'ABCD'
                }
            },
        ]
        doc = pjson.dumps(track._data)
        
        out = self.wrapper.mapPath('views/view-mbtrackid/map.js', doc)
        self.assertEquals(out, '[[["ABCD",1]]]')

    def _track_category(self, category):
        return mappings.Track(name=u'track',
            scores=[
                mappings.Score(user='thomas', category=category, score=0.8)
            ])

    def test_view_categories(self):
        track = self._track_category('Good')
        doc1 = pjson.dumps(track._data)
        doc2 = pjson.dumps(track._data)

        track = self._track_category('Rock')
        doc3 = pjson.dumps(track._data)

        out = self.wrapper.mapPath('views/view-categories/map.js', doc1)
        self.assertEquals(out, '[[["Good",1]]]')

        out = self.wrapper.mapReducePath(
            'views/view-categories/map.js',
            'views/view-categories/reduce.js',
            [doc1, doc2, doc3])
        self.assertEquals(out, '[true,[3]]')
