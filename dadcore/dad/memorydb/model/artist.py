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

    tracks = 0

    def getId(self):
        if self.id:
            return self.id

        return self.name

    def getName(self):
        return self.name

    def getSortName(self):
        return self.name

    def getTrackCount(self):
        return self.tracks


class MemoryArtistSelectorModel(artist.ArtistSelectorModel, base.MemoryModel):
    def get(self):
        return defer.succeed(self._db._artists.values())
