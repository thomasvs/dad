# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

import time

from twisted.internet import defer

from dad.model import track

from dadcouch.model import base
from dadcouch.database import mappings


# FIXME: remove track attribute
class CouchTrackModel(base.CouchScorableModel, track.TrackModel):
    """
    I represent a track in a CouchDB database.

    @ivar track: a track as returned by the database.
    """

    documentClass = mappings.Track

    # base class implementations

    @defer.inlineCallbacks
    def getOrCreate(self):
        """
        Get a backed track.

        @returns: a deferred firing a L{CouchTrackModel} object.
        """
        model = CouchTrackModel(self.database)
        trackId = self.getId()
        model.document = yield self.database.map(trackId, mappings.Track)
        defer.returnValue(model)

    def getById(self, db, trackId):
        """
        Get a track by id.

        @returns: a deferred firing a L{CouchTrackModel} object.
        """
        model = CouchTrackModel(self.database)
        model.document = yield db.map(trackId, mappings.Track)
        defer.returnValue(model)


    # FIXME: instead of forwarding, do them directly ? In subclass of Track ?
    def getName(self):
        if not self.document:
            return u"(Unknown Track)"

        return self.document.getName()

    # FIXME: add to iface ?
    @defer.inlineCallbacks
    def getArtists(self):
        models = []

        if self.document.artists:
            for artist in self.document.artists:
                # FIXME: sort name ? id ?
                model = self.database.newArtist(
                    name=artist.name, mbid=artist.mbid)
                models.append(model)

        for fragment in self.document.fragments:
            for file in fragment.files:
                if not file.metadata:
                    continue
                if not file.metadata.artist and not file.metadata.mb_artist_id:
                    continue

                # FIXME: why is this a dict and not something with attrs?
                model = yield self.database.getOrCreateArtist(
                    name=file.metadata.artist, mbid=file.metadata.mb_artist_id)
                models.append(model)

        gen = (m for m in models)
        defer.returnValue(gen)

    @defer.inlineCallbacks
    def getAlbums(self):
        models = []

        if self.document.albums:
            for album in self.document.albums:
                # FIXME: sort name ? id ?
                model = self.database.newAlbum(
                    name=album.name, mbid=getattr(album, 'mbid', None))
                models.append(model)

        for fragment in self.document.fragments:
            for file in fragment.files:
                if not file.metadata:
                    continue
                # FIXME: why is this a dict and not something with attrs?
                model = yield self.database.getOrCreateAlbum(
                    name=file.metadata.album, mbid=file.metadata.mb_album_id)
                models.append(model)

        defer.returnValue(models)

    def setName(self, name):
        self.document.name = name

    def getId(self):
        return self.document.getId()

    def getMid(self):
        return self.getId()

    def getArtistNames(self):
        if not self.document:
            return [u"(Unknown Artist)", ]

        return self.document.getArtistNames()

    def getArtistMids(self):
        return self.document.getArtistMids()

    def setCalculatedScore(self, userName, categoryName, score):
        """
        Set calculated score on a track.
        """
        return self.database.setCalculatedScore(self, userName, categoryName, score)


    def addFragment(self, info, metadata=None, mix=None, number=None,
            chroma=None):
        return self.document.addFragment(info, metadata, mix, number, chroma)

    def getFragments(self):
        return self.document.getFragments()

    # FIXME: add to iface
    def getFragmentFileByHost(self, host, extensions=None):
        """
        @type  extensions: list of str or None
        """
        # for the given track, select the highest quality file on this host
        return self.document.getFragmentFileByHost(host, extensions)


class CouchTrackSelectorModel(base.CouchDBModel):
    # FIXME: this should actually be able to pass results in as they arrive,
    # instead of everything at the end
    def get(self, cb=None, *cbArgs, **cbKWArgs):
        """
        @returns: a deferred firing a list of L{CouchTrackModel} objects.
        """
        d = defer.Deferred()

        self.debug('get')
        last = [time.time(), ]
        start = last[0]


        # FIXME: don't poke at the internals
        def loadTracks(_):
            vd = self.database._internal.viewDocs('view-tracks-title-artistid',
                mappings.TrackRow)
            def eb(f):
                print 'THOMAS: failure', f
                return f
            vd.addErrback(eb)
            return vd
        d.addCallback(loadTracks)

        def loadTracksCb(tracks):
            # tracks: list of Track
            # import code; code.interact(local=locals())
            trackList = list(tracks)
            self.debug('got %r tracks in %.3f seconds',
                len(trackList), time.time() - last[0])
            last[0] = time.time()

            ret = []
            for trackRow in trackList:
                # FIXME: find a better way to convert to a track; use a model
                track = mappings.Track()
                d = {
                    '_id': trackRow.id,
                    'name': trackRow.name,
                    'artists': trackRow.artists,
                    'albums': trackRow.albums,
                }
                track.fromDict(d)
                tm = CouchTrackModel(self.database)
                # FIXME: remove track attribute
                tm.track = track
                tm.document = track
                ret.append(tm)

            return ret


        d.addCallback(loadTracksCb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        self.debug('get(): calling back deferred chain')

        d.callback(None)
        return d
