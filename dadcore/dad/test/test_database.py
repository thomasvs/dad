# -*- Mode: Python -*- #
# vi:si:et:sw=4:sts=4:ts=4


from twisted.internet import defer

from dad.logic import database

"""
Base class for tests for database implementations.
"""

class BaseTestCase:
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
        # add a first track
        t = self.testdb.new()
        yield self.testdb.save(t)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()
        metadata.title = u'Milez iz Ded'
        metadata.artist = u'The Afghan Whigs'

        t.addFragment(info, metadata=metadata)
        ret = yield self.testdb.save(t)
        defer.returnValue(ret)

class TrackModelTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testNewSave(self):
        t = yield self.testdb.new()
        yield self.testdb.save(t)

    @defer.inlineCallbacks
    def testTrackGetName(self):
        t = yield self.testdb.new()
        t.name = u'hit me'
        yield self.testdb.save(t)

        self.assertEquals(t.getName(), u'hit me')


    @defer.inlineCallbacks
    def testScore(self):
        t = self.testdb.new()

        # make sure it gets an id
        t = yield self.testdb.save(t)

        t = yield self.testdb.score(t, u'thomas', u'Good', 0.1)
        t = yield self.testdb.score(t, u'thomas', u'Party', 0.2)

        categories = yield self.testdb.getCategories()
        self.failUnless(u'Good' in categories)
        self.failUnless(u'Party' in categories)

        scores = yield self.testdb.getScores(t)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.1)

        # update score
        yield self.testdb.score(t, u'thomas', u'Good', 0.3)

        scores = yield self.testdb.getScores(t)
        self.assertEquals(scores[0].category, u'Good')
        self.assertEquals(scores[0].score, 0.3)

    @defer.inlineCallbacks
    def testFragments(self):
        t = self.testdb.new()
        yield self.testdb.save(t)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()
        metadata.title = u'hit me'

        t.addFragment(info, metadata=metadata)
        yield self.testdb.save(t)

        # make sure we get the metadata track name back
        self.assertEquals(t.getName(), u'hit me')


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

        tracks = yield aModel.getTracks()
        tracks = list(tracks)
        self.assertEquals(len(tracks), 1)
        rtid = yield aModel.getId()
        self.assertEquals(tid, rtid)

class ArtistSelectorModelTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testArtistSelectorModel(self):
        appModel = self.provider.getAppModel(self.testdb)
        asModel = appModel.getModel('ArtistSelector')

        t = yield self.addFirstTrack()

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
        t = self.testdb.new()
        yield self.testdb.save(t)

        info = database.FileInfo('localhost', '/tmp/second.flac')
        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'

        t.addFragment(info, metadata=metadata)
        yield self.testdb.save(t)
        
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

        yield aModel.get(t.id)
        

class DatabaseTestCase(BaseTestCase):
 
    @defer.inlineCallbacks
    def testGetTracks(self):
        t = self.testdb.new()
        t.name = u'first'
        info = database.FileInfo(u'localhost', u'/tmp/first.flac')
        t.addFragment(info)
        yield self.testdb.save(t)

        gen = yield self.testdb.getTracks()
        tracks = list(gen)
        self.assertEquals(len(tracks), 1)
        self.assertEquals(tracks[0].getName(), u'first')

    @defer.inlineCallbacks
    def testGetTracksByHostPath(self):
        t = self.testdb.new()
        t.name = 'first'
        info = database.FileInfo(u'localhost', u'/tmp/first.flac')
        t.addFragment(info)
        yield self.testdb.save(t)

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
        t = self.testdb.new()
        t.name = u'first'
        info = database.FileInfo(u'localhost', u'/tmp/first.flac',
            md5sum=u'deadbeef')
        t.addFragment(info)
        t = yield self.testdb.save(t)

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

        t = yield self.testdb.trackAddFragmentFileByMD5Sum(t, 
            info, metadata)

        fragments = yield t.getFragments()
        self.assertEquals(len(fragments), 1)
        f = fragments[0]
        self.assertEquals(len(f.files), 2)


    @defer.inlineCallbacks
    def testGetTracksByMBTrackId(self):
        t = self.testdb.new()
        t.name = u'first'
        info = database.FileInfo(u'localhost', u'/tmp/milez.flac',
            md5sum=u'deadbeef')

        metadata = database.TrackMetadata()
        metadata.artist = u'The Afghan Whigs'
        mb = u'9b9b333e-8278-401b-8361-700c14096228'
        metadata.mbTrackId = mb

        t.addFragment(info, metadata=metadata)
        t = yield self.testdb.save(t)
 
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

        yield self.testdb.trackAddFragmentFileByMBTrackId(t, 
            info, metadata)

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
            DatabaseTestCase
            ]:
            name = klazz.__name__
            class testcase(cls, klazz):
                __module__ = cls.__module__
            testcase.__name__ = name
            classes[testcase.__name__] = testcase
        return classes
