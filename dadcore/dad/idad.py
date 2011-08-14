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

    def getTrackByMD5Sum(md5sum):
        """
        Look up tracks by md5sum
        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing opaque track objects.
        """


    def getTrackByMBTrackId(mbTrackId):
        """
        Look up all tracks for the musicbrainz id.

        @type  mbTrackId: unicode

        @returns: a generator returning opaque track objects for the
                  given file.
        """


    def trackAddFragment(track, host, path, md5sum, metadata=None, mix=None):
        """
        Add a file on given host and path with given md5sum to the track.

        @param metadata: L{dad.logic.database.TrackMetadata}
        """

    def trackAddFragmentFileByMD5Sum(track, info, metadata=None, mix=None):
        """
        Add the given file to each fragment with a file with the same md5sum.

        @type  info:     L{database.FileInfo}
        @type  metadata: L{database.TrackMetadata}
        @type  mix:      L{dad.audio.mix.TrackMix}
        """

    def trackAddFragmentFileByMBTrackId(track, info, metadata=None, mix=None):
        """
        Add the given file to the right fragment according to the musicbrainz
        track id.
        """


class IMetadataGetter(interface.Interface):
    def getMetadata(path, runner=None):
        """
        Get metadata from the given path.

        @type path: C{unicode}

        @rtype: L{dad.logic.database.TrackMetadata}
        """

class ILeveller(interface.Interface):
    def getTrackMixes(path, runner=None):
        """
        Get track mixes from the given path.

        @type path: C{unicode}

        @rtype: list of L{dad.audio.mix.TrackMix}
        """
