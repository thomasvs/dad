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
            name = 'dadcouch.model.daddb.TrackModel'
        elif what == 'Artist':
            name = 'dadcouch.model.daddb.ArtistModel'
        elif what == 'ArtistSelector':
            name = 'dadcouch.model.daddb.ArtistSelectorModel'
        elif what == 'Album':
            name = 'dadcouch.model.daddb.AlbumModel'
        model = reflect.namedAny(name)(self._memorydb)
        return model

        
