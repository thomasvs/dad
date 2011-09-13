# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import types

from twisted.internet import defer

from dad.common import log
from dad.logic import database

"""
Base class for tests for database implementations.
"""

class BaseTestCase(log.Loggable):
    """
    Subclass me to have database-specific tests run against the generic
    tests.

    The subclass is responsible for setting the testdb instance variable.

    @ivar testdb:   the database being tested
    @type testdb:   an implementer of L{idad.IDatabase}
    @ivar provider: the database provider
    @type provider: an implementor of L{idad.IDatabaseProvider}
    """

    @defer.inlineCallbacks
    def addFirstTrack(self):
        """
        @rtype: mappings.Track
        """
        # add a first track
        # FIXME: no name makes sense or not?
        tm = self.testdb.newTrack(name=None)
        yield self.testdb.save(tm)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()
        metadata.title = u'Milez iz Ded'
        metadata.artist = u'The Afghan Whigs'

        tm.addFragment(info, metadata=metadata)
        ret = yield self.testdb.save(tm)
        defer.returnValue(ret)

class TrackModelTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testNewSave(self):
        tm = yield self.testdb.newTrack(name=u'hit me')
        yield self.testdb.save(tm)

    @defer.inlineCallbacks
    def testTrackGetName(self):
        tm = yield self.testdb.newTrack(name=u'hit me')
        tm = yield self.testdb.save(tm)

        self.assertEquals(tm.getName(), u'hit me')


    @defer.inlineCallbacks
    def testScore(self):
        tm = yield self.testdb.newTrack(name=u'hit me')

        # make sure it gets an id
        tm = yield self.testdb.save(tm)

        tm = yield tm.setScore(u'thomas', u'Good', 0.1)
        tm = yield tm.setScore(u'thomas', u'Party', 0.2)

        categories = yield self.testdb.getCategories()
        self.failUnless(u'Good' in categories, categories)
        self.failUnless(u'Party' in categories)

        scores = yield self.testdb.getScores(tm)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.1)

        # update score
        yield tm.setScore(u'thomas', u'Good', 0.3)

        scores = yield self.testdb.getScores(tm)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.3)

    @defer.inlineCallbacks
    def testFragments(self):
        tm = yield self.testdb.newTrack(name=u'hit me')
        yield self.testdb.save(tm)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()
        metadata.title = u'hit me'

        tm.addFragment(info, metadata=metadata)
        yield self.testdb.save(tm)

        # make sure we get the metadata track name back
        self.assertEquals(tm.getName(), u'hit me')

    @defer.inlineCallbacks
    def testGetArtists(self):
        t = yield self.addFirstTrack()
        artists = yield t.getArtists()
        self.failUnless(isinstance(artists, types.GeneratorType),
            'getArtists on %r should return a generator' % t.__class__)
        a = artists.next()
        self.assertEquals(a.getName(), u'The Afghan Whigs')
        self.failIf(artists.next())

class TrackSelectorModelTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testTrackSelectorModel(self):
        appModel = self.provider.getAppModel(self.testdb)
        tsModel = appModel.getModel('TrackSelector')

        yield self.addFirstTrack()

        # check the artist selector model
        tracks = yield tsModel.get()
        self.assertEquals(len(tracks), 1)
        self.assertEquals(tracks[0].getName(), u'Milez iz Ded')
        self.assertEquals(tracks[0].getArtistNames(), [u'The Afghan Whigs', ])
        self.assertEquals(tracks[0].getArtistMids(),
            [u'artist:name:The Afghan Whigs', ])

class ArtistModelTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testArtist(self):
        aModel = self.testdb.newArtist(name=u'The Afghan Whigs')
        yield aModel.save()
        tid = yield aModel.getId()

        mid = yield aModel.getMid()

        self.failUnless(mid)

        tracks = yield aModel.getTracks()
        tracks = list(tracks)
        self.assertEquals(len(tracks), 0)

        yield self.addFirstTrack()

        mid = yield aModel.getMid()
        tracks = yield aModel.getTracks()
        tracks = list(tracks)
        self.assertEquals(len(tracks), 1)
        rtid = yield aModel.getId()
        self.assertEquals(tid, rtid)

    def testScore(self):
        am = yield self.testdb.newArtist(name=u'The Afghan Whigs')

        # make sure it gets an id
        am = yield self.testdb.save(am)

        am = yield am.setScore(u'thomas', u'Good', 0.1)
        am = yield am.setScore(u'thomas', u'Party', 0.2)

        categories = yield self.testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)

        scores = yield self.testdb.getScores(am)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.1)

        # update score
        yield am.setScore(u'thomas', u'Good', 0.3)

        scores = yield self.testdb.getScores(am)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.3)

        scores = yield am.getScores()
        self.assertEquals(len(scores), 1)

        scores = yield am.getScores(userName=u'thomas')
        self.assertEquals(len(scores), 1)

        scores = yield am.getScores(userName=u'jefke')
        self.assertEquals(len(scores), 0)


class ArtistSelectorModelTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testArtistSelectorModel(self):
        appModel = self.provider.getAppModel(self.testdb)
        asModel = appModel.getModel('ArtistSelector')

        tm = yield self.addFirstTrack()

        # check the artist selector model
        artists = yield asModel.get()
        self.assertEquals(len(artists), 1)
        name = yield artists[0].getName()
        self.assertEquals(name, u'The Afghan Whigs')
        sortname = yield artists[0].getSortName()
        self.assertEquals(sortname, u'The Afghan Whigs')
        # FIXME: id depends on database implementation
        # self.assertEquals(artists[0].getId(), u'artist:name:The Afghan Whigs')
        count = yield artists[0].getTrackCount()
        self.assertEquals(count, 1)

        # add another track
        tm = self.testdb.newTrack(name=None)
        yield self.testdb.save(tm)

        info = database.FileInfo('localhost', '/tmp/second.flac')
        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'

        tm.addFragment(info, metadata=metadata)
        yield self.testdb.save(tm)
        
        # check the artist selector model
        artists = yield asModel.get()
        self.assertEquals(len(artists), 1)
        name = yield artists[0].getName()
        self.assertEquals(name, u'The Afghan Whigs')
        count = yield artists[0].getTrackCount()
        self.assertEquals(count, 2)

    @defer.inlineCallbacks
    def testArtistController(self):
        appModel = self.provider.getAppModel(self.testdb)
        aModel = appModel.getModel('Artist')

        t = yield self.addFirstTrack()

        yield aModel.get(t.getId())
        

class DatabaseTestCase(BaseTestCase):
 
    @defer.inlineCallbacks
    def testGetTracks(self):
        tm = self.testdb.newTrack(name=u'first')
        info = database.FileInfo(u'localhost', u'/tmp/first.flac')
        tm.addFragment(info)
        yield self.testdb.save(tm)

        gen = yield self.testdb.getTracks()
        tracks = list(gen)
        self.assertEquals(len(tracks), 1)
        self.assertEquals(tracks[0].getName(), u'first')

    @defer.inlineCallbacks
    def testGetTracksByHostPath(self):
        tm = self.testdb.newTrack(name=u'first')
        info = database.FileInfo(u'localhost', u'/tmp/first.flac')
        tm.addFragment(info)
        yield self.testdb.save(tm)

        # get the right track
        gen = yield self.testdb.getTracksByHostPath(
            u'localhost', u'/tmp/first.flac')

        tracks = list(gen)
        self.assertEquals(len(tracks), 1)

        fragments = tracks[0].getFragments()
        # FIXME: should we try and make sure the same FileInfo objects
        # passed in get returned ?
        # FIXME: if not, should we implement comparison functions ?
        #self.assertEquals(fragments[0].files[0].info, info)
        self.assertEquals(fragments[0].files[0].info.path, info.path)

        # get the wrong path
        gen = yield self.testdb.getTracksByHostPath(
            u'localhost', u'/tmp/second.flac')

        tracks = list(gen)
        self.assertEquals(len(tracks), 0)

        # get the wrong host
        gen = yield self.testdb.getTracksByHostPath(
            u'localhost-2', u'/tmp/first.flac')

        tracks = list(gen)
        self.assertEquals(len(tracks), 0)

    @defer.inlineCallbacks
    def testGetTracksByMD5Sum(self):
        tm = self.testdb.newTrack(name=u'first')
        info = database.FileInfo(u'localhost', u'/tmp/first.flac',
            md5sum=u'deadbeef')
        tm.addFragment(info)
        tm = yield self.testdb.save(tm)

        # get the right track
        gen = yield self.testdb.getTracksByMD5Sum(u'deadbeef')

        tracks = list(gen)
        self.assertEquals(len(tracks), 1)

        fragments = tracks[0].getFragments()
        # FIXME: should we try and make sure the same FileInfo objects
        # passed in get returned ?
        # FIXME: if not, should we implement comparison functions ?
        #self.assertEquals(fragments[0].files[0].info, info)
        self.assertEquals(fragments[0].files[0].info.path, info.path)

        # get the wrong md5sum
        gen = yield self.testdb.getTracksByMD5Sum(u'deadbabe')

        tracks = list(gen)
        self.assertEquals(len(tracks), 0)

        # add another fragment for the same md5sum
        info = database.FileInfo(u'localhost', u'/tmp/milezisdead.flac',
            md5sum=u'deadbeef')

        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'
        mb = u'9b9b333e-8278-401b-8361-700c14096228'
        metadata.mbTrackId = mb

        tm = yield self.testdb.trackAddFragmentFileByMD5Sum(tm, 
            info, metadata)

        fragments = yield tm.getFragments()
        self.assertEquals(len(fragments), 1)
        f = fragments[0]
        self.assertEquals(len(f.files), 2)


    @defer.inlineCallbacks
    def testGetTracksByMBTrackId(self):
        tm = self.testdb.newTrack(name=u'first')
        info = database.FileInfo(u'localhost', u'/tmp/milez.flac',
            md5sum=u'deadbeef')

        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'
        mb = u'9b9b333e-8278-401b-8361-700c14096228'
        metadata.mbTrackId = mb

        tm.addFragment(info, metadata=metadata)
        tm = yield self.testdb.save(tm)
 
        # get the right track
        gen = yield self.testdb.getTracksByMBTrackId(mb)

        tracks = list(gen)
        self.assertEquals(len(tracks), 1)

        fragments = tracks[0].getFragments()
        # FIXME: should we try and make sure the same FileInfo objects
        # passed in get returned ?
        # FIXME: if not, should we implement comparison functions ?
        #self.assertEquals(fragments[0].files[0].info, info)
        self.assertEquals(fragments[0].files[0].info.path, info.path)

        # get a non-existing mb id
        gen = yield self.testdb.getTracksByMD5Sum(u'notrackid')

        tracks = list(gen)
        self.assertEquals(len(tracks), 0)
   
        # add another fragment for the same track
        info = database.FileInfo(u'localhost', u'/tmp/milez.ogg',
            md5sum=u'deadbabe')

        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'
        mb = u'9b9b333e-8278-401b-8361-700c14096228'
        metadata.mbTrackId = mb

        yield self.testdb.trackAddFragmentFileByMBTrackId(tm, 
            info, metadata)

class DatabaseInteractorTestCase(BaseTestCase):

    def setUp(self):
        self._interactor = database.DatabaseInteractor(self.testdb)


    @defer.inlineCallbacks
    def testRecalculateTrackScore(self):
        tm = yield self.addFirstTrack()

        # no scores, should not get anything
        yield self._interactor.recalculateTrackScore(tm)
        scores = yield self.testdb.getScores(tm)
        self.failIf(scores)
        scores = yield self.testdb.getCalculatedScores(tm)
        self.failIf(scores)

        # score the track directly
        tm = yield self.testdb.setScore(tm, u'thomas', u'Good', 1.0)
        tm = yield self.testdb.setScore(tm, u'thomas', u'Rock', 0.9)

        yield self._interactor.recalculateTrackScore(tm)
        scores = yield self.testdb.getScores(tm)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 1.0)

        scores = yield self.testdb.getCalculatedScores(tm)
        self.failUnless(scores)
        scores.sort(key=lambda x: x.category)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 1.0)

        # now get and score the artist
        ams = yield tm.getArtists()
        am = ams.next()
        am = yield am.setScore(u'thomas', u'Good', 0.85)

        # verify that this model in particular was scored
        scores = yield am.getScores()
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.85)

        # verify that we can get the same model through the track again,
        # with scores
        ams = yield tm.getArtists()
        am = ams.next()
        scores = yield am.getScores()
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.85)

        # verify that scores are recalculated
        yield self._interactor.recalculateTrackScore(tm)
        scores = yield self.testdb.getCalculatedScores(tm)
        self.failUnless(scores)
        self.assertEquals(scores[0].category, u'Good')
        self.assertAlmostEquals(scores[0].score, 0.92, 2)

        # now score directly through interactor
        self.debug('scoring through interactor')
        yield self._interactor.score(am, u'thomas', u'Rock', 0.8)
        scores = yield self.testdb.getCalculatedScores(tm)
        self.failUnless(scores)
        self.assertEquals(scores[1].category, u'Rock')
        self.assertAlmostEquals(scores[1].score, 0.85, 2)


def makeTestCaseClasses(cls):
        """
        Create a L{TestCase} subclass which mixes in C{cls} for each known
        test case.

        @param cls: the base class for the database-specific handling
                    including a setUp that sets testdb and provider ivars.
        """
        classes = {}
        for klazz in [
            TrackModelTestCase,
            TrackSelectorModelTestCase,
            ArtistModelTestCase,
            ArtistSelectorModelTestCase,
            DatabaseInteractorTestCase,
            DatabaseTestCase,
            ]:
            name = klazz.__name__
            class testcase(cls, klazz):
                __module__ = cls.__module__

                @defer.inlineCallbacks
                def setUp(self):
                    if hasattr(cls, 'setUp'):
                        yield cls.setUp(self)

                    if hasattr(self._klazz, 'setUp'):
                        yield self._klazz.setUp(self)

            testcase.__name__ = name
            # we can't use klazz directly in setUp, since when it's evaluated
            # it's set to the last class in the loop
            testcase._klazz = klazz
            classes[testcase.__name__] = testcase
        return classes
