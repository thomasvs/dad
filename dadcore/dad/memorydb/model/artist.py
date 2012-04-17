# -*- Mode: Python; test-case-name: dad.test.test_memorydb_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.model import artist
from dad.memorydb.model import base

class MemoryArtistModel(base.ScorableMemoryModel, artist.ArtistModel):
    """
    @ivar id:     id of the artist
    @ivar name:   name of the artist
    @type tracks: list of L{track.TrackModel}
    """
    id = None
    name = None
    mbid = None

    tracks = None

    def __init__(self, memorydb):
        base.ScorableMemoryModel.__init__(self, memorydb)
        self.tracks = []

    def new(self, db, name, sort=None, mbid=None):
        if not sort:
            sort = name

        model = MemoryArtistModel(db)
        model.name = name
        model.sortName = sort
        model.mbid = mbid
        return model
    new = classmethod(new)

    ### model implementations
    # FIXME: decide if getName can return this or def; used in __repr__
    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name
        return defer.succeed(None)

    def getSortName(self):
        return self.name

    def getId(self):
        return self.id

    def getMbId(self):
        return defer.succeed(self.mbid)

    def getTrackCount(self):
        return defer.succeed(len(self.tracks))

    def getTracks(self):
        return defer.succeed(self.tracks)

    def save(self):
        return self.database.saveArtist(self)


class MemoryArtistSelectorModel(artist.ArtistSelectorModel, base.MemoryModel):
    def get(self):
        return defer.succeed(self.database._artists.values())
