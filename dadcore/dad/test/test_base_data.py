# -*- Mode: Python; test-case-name: dad.test.test_base_data -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import simplejson

from dad.base import data

# these results have a wrong track in them
RESULTS = '''
[{"recordings": [{"duration": 305, "tracks": [{"duration": 305, "position": 6, "medium": {"release": {"id": "f03523cd-2704-428f-ba2b-80605364b04b", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}, {"duration": 305, "position": 6, "medium": {"release": {"id": "155b7e8e-6085-3ca4-88d8-9d2b2517e468", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}], "id": "0b095f83-1597-4875-a033-e9e06be4647e"}, {"duration": 302, "tracks": [{"duration": 302, "position": 9, "medium": {"release": {"id": "f2ef784f-3ea9-45e3-a673-ad3c410f2cf2", "title": "Rolling Stone: New Voices, Volume 25"}, "position": 1, "track_count": 17, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "66"}], "id": "fb3f3748-0b27-4706-a16f-dbcec83f7e72"}], "score": 1.0, "id": 1360507}, {"recordings": [{"duration": 305, "tracks": [{"duration": 305, "position": 6, "medium": {"release": {"id": "f03523cd-2704-428f-ba2b-80605364b04b", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}, {"duration": 305, "position": 6, "medium": {"release": {"id": "155b7e8e-6085-3ca4-88d8-9d2b2517e468", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}], "id": "0b095f83-1597-4875-a033-e9e06be4647e"}], "score": 0.403888, "id": 5806016}]
'''

RESULTS_DEBONAIR = '''
[{"recordings": [{"duration": 254, "tracks": [{"duration": 254, "position": 4, "medium": {"release": {"id": "9d2be14c-6a31-4bbd-a728-ad457aabe338", "title": "Gentlemen"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}, {"duration": 254, "position": 4, "medium": {"release": {"id": "840b611a-d7ae-3e0e-a0c5-149e9d918e87", "title": "Gentlemen"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "62b2952a-4605-4793-8b79-9f9745ea5da5"}, {"duration": 256, "tracks": [{"duration": 256, "position": 1, "medium": {"release": {"id": "66d9f323-023a-47b3-a198-7e796a2201ee", "title": "Debonair"}, "position": 1, "track_count": 4, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "8ff78e73-f8bd-4d78-b562-c3e939fb93fb"}, {"duration": 258, "tracks": [{"duration": 258, "position": 1, "medium": {"release": {"id": "bd206cab-d16e-446a-ad2c-5e1923276f7e", "title": "Debonair / Gentlemen"}, "position": 1, "track_count": 4, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "a0d5ced6-43e8-450a-bf11-94f1f4520b92"}, {"duration": 254, "tracks": [{"duration": 254, "position": 4, "medium": {"release": {"id": "7d072b48-b6eb-4a04-a4d0-6f3cde51a23d", "title": "Unbreakable: A Retrospective 1990-2006"}, "position": 1, "track_count": 18, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}, {"duration": 256, "position": 6, "medium": {"release": {"id": "2b287be8-18ce-4b9a-9db4-a17d81565bc1", "title": "Was het nu 70 of 80 of 90? File 1 (disc 2)"}, "position": 1, "track_count": 19, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "d01ac720-874c-48d6-95c6-a2cb66f9d5d0"}], "score": 0.971922, "id": 2085650}]
'''

class SimpleTest(unittest.TestCase):

    def testFromEmpty(self):
        f = data.ChromaPrint()
        results = simplejson.loads('[{"recordings": []}]')
        f.fromResults(results)

        self.failIf(f.metadata)

    def testFrom(self):
        f = data.ChromaPrint()
        results = simplejson.loads(RESULTS)
        f.fromResults(results)

        self.assertEquals(f.metadata.artists, ["The Afghan Whigs", ])
        self.assertEquals(f.metadata.title, "Citi Soleil")

