# -*- Mode: Python; test-case-name: dad.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base
from dad.model import scorable
from dad.common import log

class ChromaModel(base.Model):
    chromaprint = None
    duration = None
    mbid = None
    artist = None
    title = None
    lookedup = None


# FIXME: move FileInfo from dad.logic.database somewhere else ?
class FileModel(base.Model):
    """
    @type info: FileInfo
    """

    info = None
    metadata = None

class FragmentModel(base.Model):
    """
    @type files: list of subclass of L{FileModel}
    """

    def __init__(self):
        self.files = []
        self.chroma = {}

class TrackModel(scorable.ScorableModel):
    """
    I am a model for a track.

    My controller is L{dad.controller.track.TrackController}

    @ivar id:        id of the track
    @type scores:    list of L{data.Score}
    @type fragments: list of subclasses of L{FragmentModel}

    """

    # FIXME: scores ?

    id = None
    fragments = None

    def new(self, db, name, sort=None, mbid=None):
        """
        Return a new track model.

        @type  name: C{unicode}
        @type  sort: C{unicode}
        @type  mbid: C{unicode}

        @rtype: L{dad.model.track.TrackModel}
        """
    new = classmethod(new)


    def getName(self):
        """
        Return the name of the track, suitable for display.

        @rtype: C{unicode}
        """
        raise NotImplementedError

    def getArtists(self):
        """
        @rtype: L{Deferred} firing generator of L{artist.ArtistModel}
        """
        raise NotImplementedError

    def getArtistNames(self):
        """
        @rtype: list of L{unicode}
        """
        raise NotImplementedError

    def getArtistIds(self):
        """
        @rtype: list of C{unicode}
        """
        raise NotImplementedError

    def setCalculatedScore(self, userName, categoryName, score):
        """
        Set calculated score on a track.
        """
        raise NotImplementedError

    def getCalculatedScores(self, userName=None):
        """
        Get a track's calculated scores and resolve their user and category.

        @returns: L{Deferred} firing list of L{data.Score}
        """
        return self._db.getCalculatedScores(self)



    # FIXME: what does it mean if mix is None ? How does that identify
    # a fragment ?
    # FIXME: maybe metadata should be folded into info ?
    # FIXME: maybe TrackMetadata should be renamed to FileMetadata, since
    #        it's tied to a file ?
    def addFragment(self, info, metadata=None, mix=None, number=None):
        """
        Add a new fragment to the track, into the given file.

        @type  info:     L{dad.logic.database.FileInfo}
        @type  metadata: L{dad.logic.database.TrackMetadata}
        @type  mix:      L{dad.audio.mix.TrackMix}
        @type  number:   C{int}
        @param number:   the number of the fragment in the file
        """
        raise NotImplementedError

    def getFragments(self):
        """
        @rtype: list of subclasses of L{FragmentModel}
        """
        raise NotImplementedError

    def __repr__(self):
        return '<TrackModel %r for %r - %r>' % (self.id,
            " & ".join(self.getArtistNames() or []),
            self.getName())

class TrackSelectorModel(base.Model, log.Loggable):
    """
    I am a base class for a model listing all artists in the database,
    and their track count.
    """

    logCategory = 'trackselectormodel'

    tracks = None

    def get(self):
        """
        @returns: a deferred firing a list of L{dad.model.track.TrackModel}
                  objects.
        """
        raise NotImplementedError

