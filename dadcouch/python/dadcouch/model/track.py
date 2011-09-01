# -*- Mode: Python; test_case_name: dadcouch.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

import time

from twisted.internet import defer

from dad.model import track

from dadcouch.model import base
from dadcouch.database import mappings, couch


class TrackModel(base.ScorableModel, track.TrackModel):
    """
    I represent a track in a CouchDB database.

    @ivar track: a track as returned by the database.
    """

    subjectType = 'track'

    track = None


    # FIXME: instead of forwarding, do them directly ? In subclass of Track ?
    def getName(self):
        return self.track.getName()

    def getId(self):
        return self.track.getId()


    def getArtists(self):
        return self.track.getArtists()

    def getArtistMids(self):
        return self.track.getArtistMids()


    def get(self, trackId):
        """
        Get a track by id and resolve its artists.

        @returns: a deferred firing a L{TrackModel} object.
        """
        d = self._daddb.db.map(self._daddb.dbName, trackId, mappings.Track)
        #d.addCallback(lambda track:
        #    self._daddb.resolveIds(track, 'artist_ids', 'artists',
        #    mappings.Artist))

        d.addCallback(lambda track: setattr(self, 'track', track))
        d.addCallback(lambda _, s: s, self)
        return d


class TrackSelectorModel(base.CouchDBModel):
    # FIXME: this should actually be able to pass results in as they arrive,
    # instead of everything at the end
    def get(self, cb=None, *cbArgs, **cbKWArgs):
        """
        @returns: a deferred firing a list of L{TrackModel} objects.
        """
        d = defer.Deferred()

        self.debug('get')
        last = [time.time(), ]
        start = last[0]


        def loadTracks(_):
            vd = self._daddb.viewDocs('view-tracks-title-artistid', couch.TrackRow)
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
                    'artists': trackRow.artists
                }
                track.fromDict(d)
                tm = TrackModel(self._daddb)
                tm.track = track
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
