# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.python import reflect

from dad.base import app

from dad.common import log

class MemoryAppModel(app.AppModel, log.Loggable):

    logCategory = 'appmodel'

    def __init__(self, memorydb):
        self._memorydb = memorydb

    def getModel(self, what):
        # name = 'dad.models.%s.%sModel' % (what.lower(), what)
        module = what.lower()
        if module.endswith('selector'):
            module = module[:-8]
        name = 'dad.memorydb.model.%s.Memory%sModel' % (module, what, )
        # FIXME: move
        if what == 'Album':
            name = 'dadcouch.model.daddb.AlbumModel'
        model = reflect.namedAny(name)(self._memorydb)
        return model

        
