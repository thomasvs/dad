# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface
from twisted import plugin

from dad import idad

from dad.database import memory

class CoreDatabaseProvider(object):
    interface.implements(plugin.IPlugin, idad.IDatabaseProvider)

    name = 'memory'

    def getOptions(self):
        return memory.memorydb_option_list

    def getDatabase(self, options):
        return memory.MemoryDB(options.path)

    def getAppModel(self, database):
        from dad.models import app
        return app.MemoryAppModel(database)

# instantiate twisted plugins
_dp = CoreDatabaseProvider()
