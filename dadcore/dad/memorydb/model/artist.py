# -*- Mode: Python; test_case_name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.model import artist
from dad.memorydb.model import base

class MemoryArtistModel(artist.ArtistModel, base.MemoryModel):
    """
    @ivar id:     id of the artist
    @ivar name:   name of the artist
    @type tracks: int
    """
    id = None
    name = None
    mbid = None

    tracks = 0

    ### model implementations
    def getName(self):
        return defer.succeed(self.name)

    def getSortName(self):
        return defer.succeed(self.name)

    def getId(self):
        return self.id

    def getMbId(self):
        return defer.succeed(self.mbid)

    def getTrackCount(self):
        return defer.succeed(self.tracks)


class MemoryArtistSelectorModel(artist.ArtistSelectorModel, base.MemoryModel):
    def get(self):
        return defer.succeed(self._db._artists.values())
