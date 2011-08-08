# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding GStreamer-based functionality to dad command

import os

from zope import interface
from twisted import plugin

from dad import idad

from dadgst.command import analyze

# twisted.plugin interface
class CommandAppender(object):
    interface.implements(plugin.IPlugin, idad.ICommand)

    def addCommands(self, commandClass):
        commandClass.subCommandClasses.append(analyze.Analyze)


# instantiate twisted plugins
_ca = CommandAppender()
