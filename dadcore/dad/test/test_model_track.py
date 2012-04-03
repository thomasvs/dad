# -*- Mode: Python; test-case-name: dad.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

import simplejson

from dad.model import track

# these results have a wrong track in them
RESULTS = '''
[{"recordings": [{"duration": 305, "tracks": [{"duration": 305, "position": 6, "medium": {"release": {"id": "f03523cd-2704-428f-ba2b-80605364b04b", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}, {"duration": 305, "position": 6, "medium": {"release": {"id": "155b7e8e-6085-3ca4-88d8-9d2b2517e468", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}], "id": "0b095f83-1597-4875-a033-e9e06be4647e"}, {"duration": 302, "tracks": [{"duration": 302, "position": 9, "medium": {"release": {"id": "f2ef784f-3ea9-45e3-a673-ad3c410f2cf2", "title": "Rolling Stone: New Voices, Volume 25"}, "position": 1, "track_count": 17, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "66"}], "id": "fb3f3748-0b27-4706-a16f-dbcec83f7e72"}], "score": 1.0, "id": 1360507}, {"recordings": [{"duration": 305, "tracks": [{"duration": 305, "position": 6, "medium": {"release": {"id": "f03523cd-2704-428f-ba2b-80605364b04b", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}, {"duration": 305, "position": 6, "medium": {"release": {"id": "155b7e8e-6085-3ca4-88d8-9d2b2517e468", "title": "1965"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Citi Soleil"}], "id": "0b095f83-1597-4875-a033-e9e06be4647e"}], "score": 0.403888, "id": 5806016}]
'''

RESULTS_DEBONAIR = '''
[{"recordings": [{"duration": 254, "tracks": [{"duration": 254, "position": 4, "medium": {"release": {"id": "9d2be14c-6a31-4bbd-a728-ad457aabe338", "title": "Gentlemen"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}, {"duration": 254, "position": 4, "medium": {"release": {"id": "840b611a-d7ae-3e0e-a0c5-149e9d918e87", "title": "Gentlemen"}, "position": 1, "track_count": 11, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "62b2952a-4605-4793-8b79-9f9745ea5da5"}, {"duration": 256, "tracks": [{"duration": 256, "position": 1, "medium": {"release": {"id": "66d9f323-023a-47b3-a198-7e796a2201ee", "title": "Debonair"}, "position": 1, "track_count": 4, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "8ff78e73-f8bd-4d78-b562-c3e939fb93fb"}, {"duration": 258, "tracks": [{"duration": 258, "position": 1, "medium": {"release": {"id": "bd206cab-d16e-446a-ad2c-5e1923276f7e", "title": "Debonair / Gentlemen"}, "position": 1, "track_count": 4, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "a0d5ced6-43e8-450a-bf11-94f1f4520b92"}, {"duration": 254, "tracks": [{"duration": 254, "position": 4, "medium": {"release": {"id": "7d072b48-b6eb-4a04-a4d0-6f3cde51a23d", "title": "Unbreakable: A Retrospective 1990-2006"}, "position": 1, "track_count": 18, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}, {"duration": 256, "position": 6, "medium": {"release": {"id": "2b287be8-18ce-4b9a-9db4-a17d81565bc1", "title": "Was het nu 70 of 80 of 90? File 1 (disc 2)"}, "position": 1, "track_count": 19, "format": "CD"}, "artists": [{"id": "2feb192c-2363-46d6-b476-1c88a25cb294", "name": "The Afghan Whigs"}], "title": "Debonair"}], "id": "d01ac720-874c-48d6-95c6-a2cb66f9d5d0"}], "score": 0.971922, "id": 2085650}]
'''

RESULTS_BLUE_JEANS = '''
[{"recordings": 
  [{"tracks": 
    [{"duration": 209, "position": 3, "medium": {"release": {"id": "00309c41-3bd8-44f6-93e6-a04e2766a6b8", "title": "Born to Die"}, "position": 1, "track_count": 15, "format": "CD"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "21edd73f-b7c6-494e-95aa-f1390c319c9d", "title": "Born to Die"}, "position": 1, "track_count": 16, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "2f8b1ff7-4b74-499a-b229-d7f31a275eec", "title": "Born to Die"}, "position": 1, "track_count": 16, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 286, "position": 1, "medium": {"release": {"id": "6feb53b5-7487-4c1b-aa08-412e9df288f8", "title": "Born to Die"}, "position": 1, "track_count": 12, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "703f0b7c-adc3-4f9f-be85-a469ce26c89e", "title": "Born to Die"}, "position": 1, "track_count": 15, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 285, "position": 1, "medium": {"release": {"id": "86f116d9-2aed-457f-a635-b96dcf358ccd", "title": "Born to Die"}, "position": 1, "track_count": 1, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 209, "position": 3, "medium": {"release": {"id": "9c6a1a66-4ff1-4d73-a874-be627431e753", "title": "Born to Die"}, "position": 1, "track_count": 12, "format": "CD"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "9fc6de8a-8d82-4de9-a780-ad10f3ed966e", "title": "Born to Die"}, "position": 1, "track_count": 13, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 285, "position": 2, "medium": {"release": {"id": "a142f0f7-a303-4b4b-b6e7-3fb2030faa56", "title": "Lana Del Rey EP"}, "position": 1, "track_count": 4, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "aa742901-bb6a-4b92-a9b6-259f8a394fe2", "title": "Born to Die"}, "position": 1, "track_count": 12, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 286, "position": 1, "medium": {"release": {"id": "b8861fc7-75ed-415a-bd52-c6d8e10662ae", "title": "Born to Die"}, "position": 1, "track_count": 15, "format": "CD"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 2, "medium": {"release": {"id": "c50b2e04-20c3-46a5-ac69-5473a1233a14", "title": "Born to Die"}, "position": 1, "track_count": 3, "format": "CD"}, "title": "Born to Die (album version)", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 209, "position": 3, "medium": {"release": {"id": "d5955b5c-e3a7-45ed-ae4f-c80a8f7baf43", "title": "Born to Die"}, "position": 1, "track_count": 12, "format": "CD"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "df2451d1-9c95-4a08-9422-9a4931b81b33", "title": "Born to Die"}, "position": 1, "track_count": 4, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 1, "medium": {"release": {"id": "f64331cf-bc61-4391-8883-235249a0243c", "title": "Born to Die"}, "position": 1, "track_count": 15, "format": "Digital Media"}, "title": "Born to Die", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 209, "position": 3, "medium": {"release": {"id": "fa3a9f5d-2843-462d-bb60-9c44e8d16635", "title": "Born to Die"}, "position": 1, "track_count": 12, "format": "CD"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}], "id": "498bdb1b-3123-49c6-a100-309c5d4e3e31"}, {"duration": 211, "tracks": [{"duration": 0, "position": 3, "medium": {"release": {"id": "21edd73f-b7c6-494e-95aa-f1390c319c9d", "title": "Born to Die"}, "position": 1, "track_count": 16, "format": "Digital Media"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 3, "medium": {"release": {"id": "2f8b1ff7-4b74-499a-b229-d7f31a275eec", "title": "Born to Die"}, "position": 1, "track_count": 16, "format": "Digital Media"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 209, "position": 3, "medium": {"release": {"id": "6feb53b5-7487-4c1b-aa08-412e9df288f8", "title": "Born to Die"}, "position": 1, "track_count": 12, "format": "Digital Media"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 3, "medium": {"release": {"id": "703f0b7c-adc3-4f9f-be85-a469ce26c89e", "title": "Born to Die"}, "position": 1, "track_count": 15, "format": "Digital Media"}, "title": "Blue Jeans (remastered)", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 0, "position": 3, "medium": {"release": {"id": "9fc6de8a-8d82-4de9-a780-ad10f3ed966e", "title": "Born to Die"}, "position": 1, "track_count": 13, "format": "Digital Media"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 210, "position": 3, "medium": {"release": {"id": "a142f0f7-a303-4b4b-b6e7-3fb2030faa56", "title": "Lana Del Rey EP"}, "position": 1, "track_count": 4, "format": "Digital Media"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}, {"duration": 209, "position": 3, "medium": {"release": {"id": "b8861fc7-75ed-415a-bd52-c6d8e10662ae", "title": "Born to Die"}, "position": 1, "track_count": 15, "format": "CD"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}], "id": "9bf3902b-096a-4b8f-83d6-fc9b2c0d83e7"}, {"duration": 214, "tracks": [{"duration": 214, "position": 2, "medium": {"release": {"id": "2d1530cb-28ec-4445-a097-ad5eec1b38b0", "title": "Video Games: The Remix EP"}, "position": 1, "track_count": 6, "format": "CD"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}], "id": "b4b2e13f-35c1-489b-bf7f-eb1f26f587dc"}, {"duration": 212, "tracks": [{"duration": 212, "position": 2, "medium": {"release": {"id": "cca9b255-f852-4313-bd0a-d558e032946a", "title": "Video Games / Blue Jeans"}, "position": 1, "track_count": 4, "format": "Digital Media"}, "title": "Blue Jeans", "artists": [{"id": "b7539c32-53e7-4908-bda3-81449c367da6", "name": "Lana Del Rey"}]}], "id": "e5977c09-8f5a-46b6-89ea-c7bcaeae8bed"}], "score": 0.98309, "id": "b084fc23-511c-4642-955d-ba6d0bac9afa"}]
'''

class SimpleTest(unittest.TestCase):

    def testFromEmpty(self):
        f = track.ChromaPrintModel()
        results = simplejson.loads('[{"recordings": []}]')
        f.fromResults(results)

        self.failIf(f.title)
        self.failIf(f.artists)

    def testFrom(self):
        f = track.ChromaPrintModel()
        results = simplejson.loads(RESULTS)
        f.fromResults(results)

        self.assertEquals(len(f.artists), 1)
        self.assertEquals(f.artists[0]['name'], u"The Afghan Whigs")
        self.assertEquals(f.artists[0]['mbid'],
            u"2feb192c-2363-46d6-b476-1c88a25cb294")
        self.assertEquals(f.title, u"Citi Soleil")

    def testFromBlueJeans(self):
        f = track.ChromaPrintModel()
        # if we set duration, fromResults will use duration matching
        f.duration = 209
        results = simplejson.loads(RESULTS_BLUE_JEANS)
        f.fromResults(results)

        self.assertEquals(len(f.artists), 1)
        self.assertEquals(f.artists[0]['name'], u"Lana Del Rey")
        self.assertEquals(f.artists[0]['mbid'],
            u"b7539c32-53e7-4908-bda3-81449c367da6")
        self.assertEquals(f.title, u"Blue Jeans")

