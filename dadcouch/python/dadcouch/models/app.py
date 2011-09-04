# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.python import reflect

from dad.base import app

class CouchAppModel(app.AppModel):

    def __init__(self, daddb):
        self._daddb = daddb

    def getModel(self, what):
        module = what.lower()
        if 'Selector' in what:
            module = what[:-8].lower()

        name = 'dadcouch.model.%s.Couch%sModel' % (module, what)
        # name = 'dadcouch.model.daddb.%sModel' % (what, )
        model = reflect.namedAny(name)(self._daddb)
        return model

        
