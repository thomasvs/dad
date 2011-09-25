# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface
from twisted import plugin

from dad import idad

from dadcouch.command import couchdb


# twisted.plugin interface
class CommandAppender(object):
    interface.implements(plugin.IPlugin, idad.ICommand)

    def addCommands(self, commandClass):
        commandClass.subCommandClasses.append(couchdb.CouchDB)


class CouchDBDatabaseProvider(object):
    interface.implements(plugin.IPlugin, idad.IDatabaseProvider)

    name = 'couchdb'

    def getOptions(self):
        from dadcouch.selecter import couch
        return couch.couchdb_option_list

    def getDatabase(self, options):
        from dadcouch.database import couch
        from dadcouch.extern.paisley import client
        db = client.CouchDB(options.host, int(options.port))
        return couch.DADDB(db, options.database)

    def getAppModel(self, database):
        from dadcouch.models import app
        return app.CouchAppModel(database)

# instantiate twisted plugins
_ca = CommandAppender()
_dp = CouchDBDatabaseProvider()
