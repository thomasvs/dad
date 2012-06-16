# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dadcouch.extern.paisley import views

from dad.model import album

from dadcouch.database import mappings
# FIXME: rename to scorable
from dadcouch.model import base


class CouchAlbumModel(base.CouchScorableModel, album.AlbumModel):
    """
    I represent an album in a CouchDB database.
    """
    documentClass = mappings.Album

    def getName(self):
        return self.document.name

    def getSortName(self):
        return self.document.sortname

    def getId(self):
        return self.document.id

    def getMbId(self):
        return self.document.mbid

    @defer.inlineCallbacks
    def getTracks(self):
        self.debug('getTracks')
        # FIXME: this gets all possible tracks for this album, but maybe
        # this should be more limited ?
        # FIXME: what about albums with the same name by different artists?
        keys = [
            'album:name:%s' % self.getName(),
            'album:mbid:%s' % self.getMbId(),
            self.getId()
        ]

        v = views.View(self.database.db, self.database.dbName,
            'dad', 'view-tracks-by-album',
            self.database.modelFactory(ItemTracksByAlbum), keys=keys)
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

        defer.returnValue(tracks)


    @defer.inlineCallbacks
    def getOrCreate(self):
        """
        Get an album by mid, or create a new model if we can't find one.

        @returns: a deferred firing a L{CouchAlbumModel} object.
        """
        from twisted.web import error

        mid = yield self.getMid()
        self.debug('getting mid %r', mid)
        try:
            self.document = yield self.database.db.map(
                self.database.dbName, mid, mappings.Album)
        except error.Error, e:
            # FIXME: trap error.Error with 404
            self.debug('album mid %r does not exist as doc, viewing', mid)

            # get it by mid instead
            # FIXME: _internal
            ret = yield self.database._internal.viewDocs('view-album-docs', mappings.Album,
                key=mid, include_docs=True)
            albumDocs = list(ret)
            if not albumDocs:
                self.debug('aid %r can not be viewed, creating temp', mid)
                # create an empty one
                # raise IndexError(mid)
                album = yield CouchAlbumModel.new(self.database,
                    self.getName(), self.getSortName(), self.getMbId())
                # FIXME: based on aid, fill in mbid or name ?
                albums = [album, ]
            else:
                self.debug('Found albums: %r', albumDocs)
                albums = []
                for doc in albumDocs:
                    am = CouchAlbumModel(self.database)
                    am.document = doc
                    albums.append(am)

            # FIXME: multiple matches, find best one ? maybe mbid first ?
            defer.returnValue(albums[0])
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



class ItemAlbumsByArtist(CouchAlbumModel):

    tracks = 0 # int

    # of album
    name = None
    sortname = None
    id = None
    mid = None
    mbid = None

    # of artist
    artistId = None
    artistMid = None
    artistName = None
    artistSortname = None
    artistMbId = None

    # map view-albums-by-artist
    def fromDict(self, d):
        self.artistMid = d['key'][0]
        artist = d['key'][1]
        self.artistName = artist['name']
        self.artistSortname = artist['sortname']
        self.artistId = artist['id']
        self.artistMid = artist['mid']
        # FIXME: if a value is null, the key doesn't go in the dict in couch?
        self.artistMbid = artist.get('mbid', None)

        album = d['key'][2]
        self.name = album['name']
        self.sortname = album['sortname']
        self.id = album['id']
        self.mid = album['mid']
        self.mbid = album.get('mbid', None)

        self.tracks = d['value']


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
        return '<ItemAlbumsByArtist %r>' % self.name


class ItemTracksByAlbum(CouchAlbumModel):

    tracks = 0 # int

    # of album
    id = None
    mbid = None
    trackId = None

    # map view-tracks-by-album
    def fromDict(self, d):
        for key, value in d['value'].items():
            setattr(self, key, value)

    ### album.AlbumModel implementations

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
        return '<ItemTracksByAlbum %r>' % self.name



# FIXME: convert to inline deferreds
class CouchAlbumSelectorModel(base.CouchDBModel):

    logCategory = 'CouchASModel'
    artistAlbums = None # artist mid -> album ids

    def get(self):
        """
        @returns: a deferred firing a list of L{ItemAlbumsByArtist}
                  objects representing only albums and their track count.
        """
        self.debug('get')

        d = defer.Deferred()

        # first, load a mapping of artists to albums
        viewName = 'view-albums-by-artist'
        self.debug('Querying view %r', viewName)

        view = views.View(self.database.db, self.database.dbName,
            'dad', viewName,
            self.database.modelFactory(ItemAlbumsByArtist), group=True)
        d.addCallback(lambda _, v: v.queryView(), view)
        
        def cb(result):
            self.artistAlbums = {}

            result = list(result)
            self.debug('Got %d artist/albums combos', len(result))

            for item in result:
                if item.artistMid not in self.artistAlbums:
                    self.artistAlbums[item.artistMid] = []
                self.artistAlbums[item.artistMid].append(item.mid)
            return result
        d.addCallback(cb)
                    


        d.callback(None)
        return d

    def get_artists_albums(self, artist_ids):
        """
        @rtype: list of unicode
        """
        # return a list of album ids for the given list of artist ids
        # returns None if the first total row is selected, ie all artists
        ret = {}

        self.debug('Getting album ids for artist ids %r', artist_ids)
        # first row has totals, and [None}
        if None in artist_ids:
            return None

        for artist in artist_ids:
            # artists may not have albums, only tracks
            if artist in self.artistAlbums:
                for album in self.artistAlbums[artist]:
                    ret[album] = 1

        return ret.keys()
