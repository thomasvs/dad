# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import time

from twisted.internet import defer

from dadcouch.database import mappings
from dadcouch.model import track as ctrack, base
from dad.model import selection

# FIXME: remove track attribute
class CouchSelectionModel(selection.Selection, base.CouchBaseDocModel):

    documentClass = mappings.Selection

    # base class implementations

    @defer.inlineCallbacks
    def get(self, cb=None, *cbArgs, **cbKWArgs):
        """
        @returns: a deferred firing a list of L{CouchTrackModel} objects.
        """
        d = defer.Deferred()

        self.debug('get')
        last = [time.time(), ]
        start = last[0]


        
        self.debug('filtering on artist_mids %r', self.document.artist_mids)

        from dadcouch.model import artist
        tracks = yield self.database._internal.viewDocs(
            'view-tracks-by-artist',
            self.database.modelFactory(artist.ItemTracksByArtist),
            keys=self.document.artist_mids)

        trackList = list(tracks)
        self.debug('got %r tracks in %.3f seconds',
            len(trackList), time.time() - last[0])
        last[0] = time.time()

        # FIXME: this part unfinished; find a good view to use so we can
        # get all tracks by an artist
        ret = []
        for trackRow in trackList:
            print trackRow
            # FIXME: find a better way to convert to a track; use a model
            track = mappings.Track()
            d = {
                '_id': trackRow.id,
                'name': trackRow.name,
                'artists': trackRow.artists,
                'albums': trackRow.albums,
            }
            track.fromDict(d)
            tm = ctrack.CouchTrackModel(self.database)
            # FIXME: remove track attribute
            tm.track = track
            tm.document = track
            ret.append(tm)

        defer.returnValue(ret)
