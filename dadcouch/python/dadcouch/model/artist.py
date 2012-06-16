# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

import time

from twisted.internet import defer
from twisted.python import failure

from dad.common import log

from dad.model import artist
from dadcouch.model import base

from dadcouch.database import mappings
from dadcouch.extern.paisley import views

# FIXME: should be possible to create a new one through AppModel
# either empty or from db
# FIXME: remove artist for document
class CouchArtistModel(base.ScorableModel, artist.ArtistModel):
    """
    I represent an artist in a CouchDB database.
    """
    documentClass = mappings.Artist
    logCategory = 'CAModel'

    ### artist.ArtistModel implementations
    def getName(self):
        return self.document.name

    def setName(self, name):
        # FIXME: this is ugly, self.document should be set already
        if not self.document:
            self.document = mappings.Artist()

        self.document.name = name
        return defer.succeed(None)

    def getSortName(self):
        return self.document.sortname

    def getId(self):
        return self.document.id

    def getMbId(self):
        return self.document.mbid

    ### FIXME: to be implemented
    def getTrackCount(self):
        return 424242

    @defer.inlineCallbacks
    def getTracks(self):
        self.debug('getTracks')
        # FIXME: this gets all possible tracks for this artist, but maybe
        # this should be more limited ?
        keys = [
            'artist:name:%s' % self.getName(),
            'artist:mbid:%s' % self.getMbId(),
            self.getId()
        ]

        v = views.View(self.database.db, self.database.dbName,
            'dad', 'view-tracks-by-artist',
            self.database.modelFactory(ItemTracksByArtist), keys=keys)
        try:
            result = yield v.queryView()
        except Exception, e:
            self.warning('get: exception: %r', log.getExceptionMessage(e))
            raise

        # FIXME: instead of doing a loop, create them from the view directly
        tracks = []
        for r in result:
            tm = yield self.database.getTrack(r.trackId)
            tracks.append(tm)

        self.debug('getTracks: returning %r', tracks)
        defer.returnValue(tracks)


    def save(self):
        return self.database.save(self)

    ### FIXME: to be added to iface ?
    ### FIXME: make it a class method too

    @defer.inlineCallbacks
    def getOrCreate(self):
        """
        Get an artist by mid, or create a new model if we can't find one.

        @returns: a deferred firing a L{CouchArtistModel} object.
        """
        from twisted.web import error

        mid = yield self.getMid()
        self.debug('getting mid %r', mid)
        try:
            self.document = yield self.database.db.map(
                self.database.dbName, mid, mappings.Artist)
        except error.Error, e:
            # FIXME: trap error.Error with 404
            self.debug('aid %r does not exist as doc, viewing', mid)

            # get it by aid instead
            # FIXME: _internal
            ret = yield self.database._internal.viewDocs('view-artist-docs', mappings.Artist,
                key=mid, include_docs=True)
            artistDocs = list(ret)
            if not artistDocs:
                self.debug('aid %r can not be viewed, creating temp', mid)
                # create an empty one
                # raise IndexError(mid)
                artist = yield CouchArtistModel.new(self.database,
                    self.getName(), self.getSortName(), self.getMbId())
                # FIXME: based on aid, fill in mbid or name ?
                artists = [artist, ]
            else:
                self.debug('Found artists: %r', artistDocs)
                artists = []
                for doc in artistDocs:
                    am = CouchArtistModel(self.database)
                    am.document = doc
                    artists.append(am)

            # FIXME: multiple matches, find best one ? maybe mbid first ?
            defer.returnValue(artists[0])
            return

        except Exception, e:
                self.warningFailure(failure.Failure(e))
                self.controller.doViews('error', "failed to populate",
                   "%r: %r" % (e, e.args))
                raise IndexError(mid)
                #defer.returnValue(None)
                #return

        self.debug('found document %r', self.document)
        defer.returnValue(self)


# FIXME: rename
class ItemTracksByArtist(CouchArtistModel):

    tracks = 0 # int

    # of artist
    id = None
    mbid = None
    trackId = None

    # map view-tracks-by-artist
    def fromDict(self, d):
        for key, value in d['value'].items():
            setattr(self, key, value)

    ### artist.ArtistModel implementations

    def getName(self):
        return self.name

    def getSortName(self):
        return self.sortname

    def getId(self):
        return self.id

    def getMbId(self):
        return self.mbid

    def getTrackCount(self):
        return self.tracks

    def __repr__(self):
        return '<ItemTracksByArtist %r>' % self.name


class CouchArtistSelectorModel(artist.ArtistSelectorModel, base.CouchDBModel):

    logCategory = 'CASelModel'

    @defer.inlineCallbacks
    def get(self):
        """
        @returns: a deferred firing a list of L{daddb.ItemTracksByArtist}
                  objects representing only artists and their track count.
        """
        start = time.time()

        self.debug('get')
        v = views.View(self.database.db, self.database.dbName,
            'dad', 'view-tracks-by-artist',
            self.database.modelFactory(ItemTracksByArtist))
        try:
            itemTracks = yield v.queryView()
        except Exception, e:
            self.warning('get: exception: %r', log.getExceptionMessage(e))
            raise

        # convert list of ordered itemTracks
        # into a list of ItemTracks with track counts
        artists = {} # mid -> name, id, count

        for item in itemTracks:
            mid = yield item.getMid()
            if mid not in artists:
                artists[mid] = item
            artists[mid].tracks += 1

        ret = artists.values()

        self.debug('get: got %d artists in %.3f seconds',
            len(ret), time.time() - start)

        defer.returnValue(ret)
