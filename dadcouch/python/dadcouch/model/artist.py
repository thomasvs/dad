# -*- Mode: Python; test_case_name: dadcouch.test.test_model_daddb -*-
# vi:si:et:sw=4:sts=4:ts=4

import time

from twisted.internet import defer
from twisted.python import failure

from dad.common import log

from dad.model import artist
from dadcouch.model import base

from dadcouch.database import mappings
from dadcouch.extern.paisley import views

class ArtistModel(base.ScorableModel, artist.ArtistModel):
    """
    I represent an artist in a CouchDB database.
    """
    subjectType = 'artist'

    artist = None

    ### artist.ArtistModel implementations
    def getName(self):
        return self.artist.name

    def getSortName(self):
        return self.artist.sortname

    def getId(self):
        return self.artist.id

    def getMbId(self):
        return self.artist.mbid

    ### FIXME: to be implemented
    def getTrackCount(self):
        return 424242


    ### FIXME: to be added to iface ?

    @defer.inlineCallbacks
    def get(self, mid):
        """
        Get an artist by mid.

        @returns: a deferred firing a L{ArtistModel} object.
        """
        from twisted.web import error

        self.debug('getting mid %r', mid)
        try:
            # FIXME: fix subject vs artist
            self.subject = yield self._daddb.db.map(
                self._daddb.dbName, mid, mappings.Artist)
            self.artist = self.subject
        except error.Error, e:
            # FIXME: trap error.Error with 404
            self.debug('aid %r does not exist as doc, viewing', mid)

            # get it by aid instead
            ret = yield self._daddb.viewDocs('view-artist-docs', mappings.Artist,
                key=mid, include_docs=True)
            artists = list(ret)
            if not artists:
                self.debug('aid %r can not be viewed, creating temp', mid)
                # create an empty one
                # raise IndexError(mid)
                artist = mappings.Artist()
                artist.name = self.getName()
                artist.sortname = self.sortname
                artist.mbid = self.getMbId()
                self.debug('Creating temporary model from self %r to %r',
                    self, artist)
                # FIXME: based on aid, fill in mbid or name ?
                artists = [artist, ]
            else:
                self.debug('Found artists: %r', artists)

            # FIXME: multiple matches, find best one ? maybe mbid first ?
            self.subject = ArtistModel(self._daddb)
            self.artist = self.subject
            self.subject.artist = artists[0]
            defer.returnValue(self.subject)
            return
            
        except Exception, e:
                self.warningFailure(failure.Failure(e))
                self.controller.doViews('error', "failed to populate",
                   "%r: %r" % (e, e.args))
                raise IndexError(mid)
                #defer.returnValue(None)
                #return

        self.debug('found subject %r', self.subject)
        defer.returnValue(self)

    # In addition to scoring the artist, we want to update calculated scores
    # for tracks and albums
    @defer.inlineCallbacks
    def score(self, subject, userName, categoryName, score):
        subject = yield base.ScorableModel.score(
            subject, userName, categoryName, score)

        # now get all tracks for this artist
        doc = getattr(subject, self.subjectType)
        doc = yield self._daddb.score(doc, userName, categoryName, score)
        setattr(subject, self.subjectType, doc)
        defer.returnValue(subject)

# FIXME: rename
class ItemTracksByArtist(ArtistModel):

    tracks = 0 # int
    id = None
    mbid = None
    trackId = None

    _daddb = None

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


class ArtistSelectorModel(artist.ArtistSelectorModel, base.CouchDBModel):
    def get(self):
        """
        @returns: a deferred firing a list of L{daddb.ItemTracksByArtist}
                  objects representing only artists and their track count.
        """
        start = time.time()
        self.debug('get')
        v = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'view-tracks-by-artist',
            self._daddb.modelFactory(ItemTracksByArtist))
        try:
            d = v.queryView()
        except Exception, e:
            self.warning('get: exception: %r', log.getExceptionMessage(e))
            return defer.fail(e)

        def cb(itemTracks):
            # convert list of ordered itemTracks
            # into a list of ItemTracks with track counts
            artists = {} # artist sortname -> name, id, count

            for item in itemTracks:
                if item.sortname not in artists:
                    artists[item.sortname] = item
                artists[item.sortname].tracks += 1

            ret = artists.values()

            self.debug('get: got %d artists in %.3f seconds',
                len(ret), time.time() - start)
            return ret
        d.addCallback(cb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        return d
