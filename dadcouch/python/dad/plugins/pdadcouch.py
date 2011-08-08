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


# instantiate twisted plugins
_ca = CommandAppender()

