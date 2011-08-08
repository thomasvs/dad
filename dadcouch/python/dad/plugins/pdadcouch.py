# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface
from twisted import plugin

from dad import idad

# twisted.plugin interface
class CommandAppender(object):
    interface.implements(plugin.IPlugin, idad.ICommand)

    def addCommands(self, commandClass):
        from dadcouch.command import plugin as p
        commandClass.subCommandClasses.append(p.Lookup)


# instantiate twisted plugins
_ca = CommandAppender()

