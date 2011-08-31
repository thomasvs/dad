# -*- Mode: Python; test_case_name: dadcouch.test.test_model_daddb -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import time

from twisted.internet import defer
from twisted.python import failure

from zope import interface

from dadcouch.extern.paisley import mapping
from dadcouch.extern.paisley import views

from dad import idad
from dad.common import log
from dad.model import artist

from dadcouch.common import manydef

from dadcouch.model import base
from dadcouch.database import mappings, couch


class TrackSelectorModel(base.CouchDBModel):
    # FIXME: this should actually be able to pass results in as they arrive,
    # instead of everything at the end
    def get(self, cb=None, *cbArgs, **cbKWArgs):
        """
        @returns: a deferred firing a list of L{database.TrackRow} objects.
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
                ret.append(track)

            return ret


        d.addCallback(loadTracksCb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        self.debug('get(): calling back deferred chain')

        d.callback(None)
        return d


class TrackModel(base.ScorableModel):
    """
    I represent a track in a CouchDB database.

    @ivar track: a track as returned by the database.
    """

    subjectType = 'track'

    track = None

    def get(self, trackId):
        """
        Get a track by id and resolve its artists.

        @returns: a deferred firing a L{mappings.Track} object.
        """
        d = self._daddb.db.map(self._daddb.dbName, trackId, mappings.Track)
        #d.addCallback(lambda track:
        #    self._daddb.resolveIds(track, 'artist_ids', 'artists',
        #    mappings.Artist))

        d.addCallback(lambda track: setattr(self, 'track', track))
        d.addCallback(lambda _, s: s.track, self)
        return d
