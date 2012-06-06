# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import random
import time

from twisted.internet import defer

from dad.model import selection
from dad.common import iterators

from dadcouch.database import mappings
from dadcouch.model import base


# FIXME: remove track attribute
class CouchSelectionModel(selection.Selection, base.CouchBaseDocModel):

    documentClass = mappings.Selection

    # base class implementations

    @defer.inlineCallbacks
    def get(self, cb=None, *cbArgs, **cbKWArgs):
        """
        @returns: a deferred firing a generator of L{CouchTrackModel} objects.
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

        artists = []
        gens = []

        # FIXME: reduce this somewhere
        for trackRow in trackList:
            mid = yield trackRow.getMid()
            if mid in artists:
                continue
            artists.append(mid)

            tracks = yield trackRow.getTracks()
            tracks = list(tracks)
            random.shuffle(tracks)
            gens.append((t for t in tracks))
            random.shuffle(gens)

        defer.returnValue(iterators.tmerge(*gens))
