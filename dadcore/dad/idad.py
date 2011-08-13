# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface

"""
Interfaces for functionality provided by add-on modules.
"""

class ICommand(interface.Interface):
    def addCommands(commandClass):
        pass

class IDatabaseProvider(interface.Interface):
    """
    I am an interface for a provider of a database.
    """

    name = interface.Attribute("""
        @type name: C{str}
        @ivar name: the short name of the database provider
        """)

    def getOptions():
        """
        Get the options that can be used to instantiate a database.
        """
        pass

    def getDatabase(options):
        """
        Return a new Database with the given options.
        """
        pass

class IDatabase(interface.Interface):
    """
    I am an interface for databases.
    """

    def getTrackByHostPath(host, path):
        """
        @type  host: unicode
        @param host: the host on which the file lives
        @type  path: unicode
        @param path: the path where the file lives
        """
        pass

class IAnalyzer(interface.Interface):
    pass

