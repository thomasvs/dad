# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface

class ICommand(interface.Interface):
    def addCommands(commandClass):
        pass

class IDatabaseProvider(interface.Interface):
    pass

class IAnalyzer(interface.Interface):
    pass

