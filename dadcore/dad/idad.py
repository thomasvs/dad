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

    def new():
        """
        Return a new track data object that can be handed to calls.
        """

    def save(track):
        """
        Save the given track in the database.
        """
        return self.daddb.saveDoc(track)

    def getTrackByHostPath(host, path):
        """
        Look up all tracks for the given host and path.

        @type  host: unicode
        @param host: the host on which the file lives
        @type  path: unicode
        @param path: the path where the file lives

        @returns: a generator returning opaque track objects for the
                  given file.
        """

    def trackAddFragment(track, host, path, md5sum):
        """
        Add a file on given host and path with given md5sum to the track.
        """

class MetadataGetter(interface.Interface):
    pass

class IAnalyzer(interface.Interface):
    pass

