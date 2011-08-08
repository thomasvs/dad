# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface

"""
Interfaces for functionality provided by add-on modules.
"""

class ICommand(interface.Interface):
    def addCommands(commandClass):
        pass

class IDatabase(interface.Interface):
    def lookupPath(path):
        """
        @type path: unicode
        """
        pass

class IAnalyzer(interface.Interface):
    pass

