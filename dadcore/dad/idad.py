# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from zope import interface

"""
Interfaces for functionality provided by add-on modules.
"""

class NoPlugin(Exception):
    """
    No plugin found for the given plugin interface.
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

class IPlayerProvider(interface.Interface):
    """
    I am an interface for a provider of a player.
    """

    name = interface.Attribute("""
        @type name: C{str}
        @ivar name: the short name of the player provider
        """)

    def getOptions():
        """
        Get the options that can be used to instantiate a player.
        """
        pass

    def getPlayer(scheduler, options):
        """
        Return a new Player with the given scheduler and options.
        """
        pass


class IDatabase(interface.Interface):
    """
    I am an interface for databases.
    """

    # FIXME: remove
    def new():
        """
        Return a new track data object that can be handed to calls.
        """

    def newTrack(name, sort=None, mbid=None):
        """
        Return a new track model.

        @type  name: C{unicode}
        @type  sort: C{unicode}
        @type  mbid: C{unicode}

        @rtype: L{dad.model.track.TrackModel}
        """

    def newArtist(name, sort=None, mbid=None):
        """
        Return a new artist model.

        @type  name: C{unicode}
        @type  sort: C{unicode}
        @type  mbid: C{unicode}

        @rtype: L{dad.model.artist.ArtistModel}
        """

    def save(track):
        """
        Save the given track in the database.
        """

    def getTracks():
        """
        Look up all tracks.

        @returns: a generator returning opaque track objects.
        """

    def addCategory(name):
        """
        @type  name: C{unicode}

        Add a category.
        """

    def getCategories():
        """
        Get a list of all categories.

        @returns: a deferred firing a generator of category names.
        @rtype:   L{twisted.internet.defer.Deferred} firing C{list} of
                  C{unicode}
        """

    def getScores(subject):
        """
        @type  subject: a subclass of L{dad.model.artist.TrackModel} or others

        @returns: deferred firing list of L{dad.base.data.Score}
        """

    def getTracksByHostPath(host, path):
        """
        Look up all tracks for the given host and path.

        @type  host: unicode
        @param host: the host on which the file lives
        @type  path: unicode
        @param path: the path where the file lives

        @rtype: a L{defer.Deferred} firing a generator
                returning subclasses of L{dad.model.track.TrackModel}
        """

    def getTracksByMD5Sum(md5sum):
        """
        Look up tracks by md5sum
        Can return multiple tracks for a path; for example, multiple
        fragments.

        @rtype: a L{defer.Deferred} firing a generator
                returning subclasses of L{dad.model.track.TrackModel}
        """


    def getTracksByMBTrackId(mbTrackId):
        """
        Look up all tracks for the musicbrainz id.

        @type  mbTrackId: unicode

        @returns: a generator returning opaque track objects for the
                  given file.
        """


    def trackAddFragment(track, host, path, md5sum, metadata=None, mix=None, number=None):
        """
        Add a file on given host and path with given md5sum to the track.

        @param metadata: L{dad.logic.database.TrackMetadata}
        """

    def trackAddFragmentFileByMD5Sum(track, info, metadata=None, mix=None, number=None):
        """
        Add the given file to each fragment with a file with the same md5sum.

        @type  info:     L{dad.logic.database.FileInfo}
        @type  metadata: L{dad.logic.database.TrackMetadata}
        @type  mix:      L{dad.audio.mix.TrackMix}
        """

    def trackAddFragmentFileByMBTrackId(track, info, metadata=None, mix=None, number=None):
        """
        Add the given file to the right fragment according to the musicbrainz
        track id.
        """

    def setScore(subject, userName, categoryName, score):
        """
        Score the given subject.
        The database backend should store the score and related information.
        For example, the category should exist and be retrievable with
        getCategories() after this call.

        @type  subject:      subclass of L{dad.model.track.TrackModel} or others
        @type  userName:     C{unicode}
        @type  categoryName: C{unicode}
        @param score:        A score between 0.0 and 1.0
        @type  score:        C{float}

        @rtype: a L{twisted.internet.defer.Deferred} firing a subclass of the
                update L{dad.model.track.TrackModel} or other
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

class IChromaPrinter(interface.Interface):
    def getChromaPrint(path, runner=None):
        """
        Get chromaprint from the given path.

        @type path: C{unicode}

        @rtype: C{str}
        """
