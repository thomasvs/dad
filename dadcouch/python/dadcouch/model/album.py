# -*- Mode: Python; test_case_name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dadcouch.extern.paisley import views

from dadcouch.database import mappings, couch
from dadcouch.model import base

class CouchAlbumModel(base.ScorableModel):
    """
    I represent an album in a CouchDB database.
    """
    subjectType = 'album'

    album = None

    def get(self, albumId):
        """
        Get an artist by id.

        @returns: a deferred firing a L{mappings.Album} object.
        """
        d = self._daddb.db.map(self._daddb.dbName, albumId, mappings.Album)

        d.addCallback(lambda album: setattr(self, 'album', album))
        d.addCallback(lambda _, s: s.album, self)
        return d

# FIXME: convert to inline deferreds
class CouchAlbumSelectorModel(base.CouchDBModel):

    artistAlbums = None # artist id -> album ids

    def get(self):
        """
        @returns: a deferred firing a list of L{couch.ItemAlbumsByArtist}
                  objects representing only albums and their track count.
        """
        self.debug('get')

        d = defer.Deferred()

        # first, load a mapping of artists to albums
        view = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'view-albums-by-artist',
            couch.ItemAlbumsByArtist, group=True)
        d.addCallback(lambda _, v: v.queryView(), view)
        
        def cb(result):
            self.artistAlbums = {}

            result = list(result)
            self.debug('Got %d artist/albums combos', len(result))

            for item in result:
                if item.artistId not in self.artistAlbums:
                    self.artistAlbums[item.artistId] = []
                self.artistAlbums[item.artistId].append(item.id)
            return result
        d.addCallback(cb)
                    


        d.callback(None)
        return d

    def get_artists_albums(self, artist_ids):
        """
        @rtype: list of str
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


