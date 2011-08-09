# -*- Mode: Python; test-case-name: dad.test.test_base_data -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import simplejson

from dad.base import fingerprint

RESULTS = '''
[{"recordings": [{"duration": 305, "tracks": [{"duration": 305, "position": 6, "medium": {"release": {"id": "f03523cd-2704-428f-ba2b-80605364b04b", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}, {"duration": 305, "position": 6, "medium": {"release": {"id": "155b7e8e-6085-3ca4-88d8-9d2b2517e468", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}], "id": "0b095f83-1597-4875-a033-e9e06be4647e"}, {"duration": 302, "tracks": [{"duration": 302, "position": 9, "medium": {"release": {"id": "f2ef784f-3ea9-45e3-a673-ad3c410f2cf2", "title": "Rolling Stone: New Voices, Volume 25"}, "position": 1, "track_count": 17, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "66"}], "id": "fb3f3748-0b27-4706-a16f-dbcec83f7e72"}], "score": 1.0, "id": 1360507}, {"recordings": [{"duration": 305, "tracks": [{"duration": 305, "position": 6, "medium": {"release": {"id": "f03523cd-2704-428f-ba2b-80605364b04b", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}, {"duration": 305, "position": 6, "medium": {"release": {"id": "155b7e8e-6085-3ca4-88d8-9d2b2517e468", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}], "id": "0b095f83-1597-4875-a033-e9e06be4647e"}], "score": 0.403888, "id": 5806016}]
'''

class SimpleTest(unittest.TestCase):

    def testFrom(self):
        f = fingerprint.ChromaPrint()
        results = simplejson.loads(RESULTS)
        f.fromResults(results)

        self.assertEquals(f.metadata.artists, ["The Afghan Whigs", ])
        self.assertEquals(f.metadata.title, "Citi Soleil")

