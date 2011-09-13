# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from zope import interface

from dadcouch.extern.paisley import mapping

from dad import idad
from dad.common import log

from dadcouch.database import mappings, internal
from dadcouch.model import base, artist, track

# value to use for ENDKEY when looking up strings
# FIXME: something better; with unicode ?
ENDKEY_STRING = "z"

# generic row mapping, with id
class GenericIdRow:
    def fromDict(self, d):
        self.id = d['id']
        self.key = d['key']
        self.value = d['value']

class GenericRow:
    def fromDict(self, d):
        self.key = d['key']
        self.value = d['value']


# map track-score view
class TrackScore(mapping.Document):
    categoryId = mapping.TextField()
    userId = mapping.TextField()
    subjectId = mapping.TextField()
    score = mapping.FloatField()

    def fromDict(self, d):
        self.categoryId = d['key'][0]
        self.userId = d['key'][1]
        self.subjectId = d['key'][2]
        self.score = float(d['value'])


# map score view results
class ScoreRow(mapping.Document):
    id = mapping.TextField()
    user = mapping.TextField()
    category = mapping.TextField()
    score = mapping.FloatField()

    def fromDict(self, d):
        self.id = d['id']
        self.name = d['key']
        self.user, self.category, self.score = d['value']

# map view-scores-host
class ViewScoresHostRow:

    def fromDict(self, d):
        self.id = d['id']
        self.name = d['key']
        self.user, self.category, self.score = d['key']
        self.hosts = d['value']
        self.track = mappings.Track()
        self.track.fromDict(d['doc'])

    def __repr__(self):
        return '<Score %.3f for user %r in category %r for %r on %r>' % (
            self.score, self.user, self.category, self.id, self.hosts)

class ItemAlbumsByArtist:

    tracks = 0 # int
    artistName = None
    artistSortname = None
    artistId = None

    # of album
    name = None
    sortname = None
    id = None

    # map view-albums-by-artist
    # key: artist name, sortname, id; album name, sortname, id
    # value: track count
    def fromDict(self, d):
        self.artistName, self.artistSortname, self.artistId, self.name, self.sortname, self.id = d['key']

        self.tracks = d['value']

    def getMid(self):
        # FIXME
        return self.id

class ItemTracks:
    # map tracks-by-album and tracks-by-artist
    def fromDict(self, d):
        self.type = d['key'][1] # 0 for artist/album row, 1 for trackm row

        v = d['value']

        if self.type == 0:
            # artist/album row, full doc
            self.name = v['name']
            self.sortname = v.get('sortname', v['name'])
            self.id = d['id']

            # will be set in a callback to count tracks on this album
            self.tracks = 0
        else:
            # trackalbum, only track_id
            self.trackId = d['id']

class AlbumsByArtist:
    # map albums-by-artist
    def fromDict(self, d):
        self.type = d['key'][1] # 0 for artist row, 1 for album row

        v = d['value']

        if self.type == 0:
            # artist
            self.name = v['name']
            self.sortname = v.get('sortname', v['name'])
            self.id = d['id']
            self.albums = []
        else:
            # album
            self.albumId = d['id']


class DADDB(log.Loggable):
    """
    @type  db:     L{dadcouch.extern.paisley.client.CouchDB}
    @type  dbName: str
    """

    interface.implements(idad.IDatabase)

    logCategory = 'daddb'

    def __init__(self, db, dbName):
        """
        @type  db:     L{dadcouch.extern.paisley.client.CouchDB}
        @type  dbName: str
        """
        self.db = db
        self.dbName = dbName

        self._internal = internal.InternalDB(db, dbName)

    ## idad.IDatabase interface
    def newTrack(self, name, sort=None, mbid=None):
        return track.CouchTrackModel.new(self, name, sort, mbid)

    def newArtist(self, name, sort=None, mbid=None):
        return artist.CouchArtistModel.new(self, name, sort, mbid)

    @defer.inlineCallbacks
    def getOrCreateArtist(self, name, sort=None, mbid=None):
        # look up by mbid or name
        mid = None
        if mbid:
            mid = u'artist:mbid:' + mbid
        elif name:
            mid = u'artist:name:' + name

        if mid:
            self.debug('Looking up by mid %r', mid)
            # FIXME: convert to class method ?
            model = yield artist.CouchArtistModel.new(self, name, sort, mbid)
            model = yield model.get(mid)
            self.debug('Looked up by mid %r, model %r', mid, model)

        if not model:
            self.debug('Creating new artist for mid %r', mid)
            model = yield artist.CouchArtistModel.new(self, name, sort, mbid)

        defer.returnValue(model)


    # FIXME: use internal save ?
    @defer.inlineCallbacks
    def save(self, item):
        """
        @type item; L{base.CouchDocModel}
        """
        if isinstance(item, base.CouchDocModel):
            stored = yield self._internal.saveDoc(item.document)
            # FIXME: for now, look it up again to maintain the track illusion
            item.document = yield self._internal.db.map(
                self.dbName, stored['id'],
                item.document.__class__)
            self.debug('saved item doc %r', item.document)
            defer.returnValue(item)
        else:
            raise AttributeError, \
                "Cannot save item of class %r" % item.__class__

    # FIXME: this actually still yields models I think
    def getTracks(self):
        return self._internal.getTracks()

    @defer.inlineCallbacks
    def setScore(self, subject, userName, categoryName, score):
        """
        @type subject: L{base.ScorableModel}
        """
        assert isinstance(subject, base.ScorableModel), \
            "subject %r is not a scorable" % subject
        doc = yield self._internal.setScore(subject.document,
            userName, categoryName, score)
        subject.document = doc
        defer.returnValue(subject)

    def getScores(self, subject):
        """
        @returns: deferred firing list of L{data.Score}
        """
        assert isinstance(subject, base.ScorableModel), \
            "subject %r is not scorable" % subject
        return self._internal.getScores(subject.document)

    def getCalculatedScores(self, tm):
        """
        @returns: deferred firing list of L{data.Score}
        """
        assert isinstance(tm, track.CouchTrackModel), \
            "track %r is not a track" % track
        return self._internal.getCalculatedScores(tm.document)

    @defer.inlineCallbacks
    def setCalculatedScore(self, subject, userName, categoryName, score):
        """
        @type subject: L{track.TrackModel}
        """
        assert isinstance(subject, track.CouchTrackModel), \
            "subject %r is not a scorable" % subject
        doc = yield self._internal.setCalculatedScore(subject.document,
            userName, categoryName, score)
        subject.document = doc
        defer.returnValue(subject)


    def addCategory(self, name):
        return self._internal.addCategory(name)

    def getCategories(self):
        return self._internal.getCategories()

    def getTracksByHostPath(self, host, path):
        """
        Look up tracks by path.
        Can return multiple tracks for a path; for example, multiple
        fragments.


        @type  host: unicode
        @type  path: unicode

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{mappings.Track}
        """
        return self._internal.getTracksByHostPath(host, path)

    def trackAddFragment(self, track, info, metadata=None, mix=None, number=None):
        return track.addFragment(info, metadata, mix, number)

    # FIXME: what do we return ?
    def getTracksByMD5Sum(self, md5sum):
        """
        Look up tracks by md5sum
        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{mappings.Track}
        """
        return self._internal.getTracksByMD5Sum(md5sum)

    def getTracksByMBTrackId(self, mbTrackId):
        """
        Look up tracks by musicbrainz track id.

        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{mappings.Track}
        """
        return self._internal.getTracksByMBTrackId(mbTrackId)

    def trackAddFragmentFileByMD5Sum(self, track, info, metadata=None, mix=None, number=None):
        """
        Add the given file to each fragment with a file with the same md5sum.
        """
        return self._internal.trackAddFragmentFileByMD5Sum(
            track.document, info, metadata, mix, number)

    def trackAddFragmentFileByMBTrackId(self, track, info, metadata, mix=None, number=None):
        return self._internal.trackAddFragmentFileByMBTrackId(
            track.document, info, metadata, mix, number)

    @defer.inlineCallbacks
    def getPlaylist(self, hostName, userName, categoryName, above, below, limit=None,
        random=False):
        """
        @type  limit:        int or None
        @type  random:       bool

        @returns: list of tracks and additional info, ordered by track id
        @rtype: L{defer.Deferred} firing
                list of Track, Slice, path, score, userId
        """
        self.debug('Getting tracks for host %r and category %r and user %r',
            hostName, categoryName, userName)

        startkey = [userName, categoryName, above]
        endkey = [userName, categoryName, below]

        gen = yield self.viewDocs('view-scores-host', mappings.Track,
            startkey=startkey, endkey=endkey, include_docs=True)

        # FIXME: filter on host ?

        # FIXME: for randomness, we currently go from generator to
        # full list and back
        if random:
            tracks = list(gen)
            import random
            random.shuffle(tracks)
            gen = (t for t in tracks)

        defer.returnValue(gen)

    ### own instance methods
    def map(self, docId, objectFactory):
        return self.db.map(self.dbName, docId, objectFactory)

    def modelFactory(self, modelClass):
        return lambda: modelClass(daddb=self)
