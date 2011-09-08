# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.model import album
from dad.memorydb.model import base

class MemoryAlbumSelectorModel(album.AlbumSelectorModel, base.MemoryModel):
    def get(self):
        # FIXME: implement
        return defer.succeed([])
        return defer.succeed(self._db._artists.values())
