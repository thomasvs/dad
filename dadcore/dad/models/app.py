# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.python import reflect

from dad.base import app

class MemoryAppModel(app.AppModel):

    def __init__(self, memorydb):
        self._memorydb = memorydb

    def getModel(self, what):
        name = 'dad.models.%s.%sModel' % (what.lower(), what)
        # FIXME: move
        if what == 'Track':
            name = 'dad.database.memory.MemoryTrackModel'
        elif what == 'Artist':
            name = 'dad.database.memory.MemoryArtistModel'
        elif what == 'ArtistSelector':
            name = 'dad.database.memory.MemoryArtistSelectorModel'
        elif what == 'Album':
            name = 'dadcouch.model.daddb.AlbumModel'
        model = reflect.namedAny(name)(self._memorydb)
        return model

        
