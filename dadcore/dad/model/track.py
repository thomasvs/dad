# -*- Mode: Python; test-case-name: dad.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base
from dad.model import scorable, selector

# FIXME: add tests for fromResults
class ChromaPrintModel(base.Model):
    """
    @type  chromaprint: C{str}
    @type  mbid:        C{str}
    @param artists:     list of dict of name, mbid of artists
    @type  artists:     list of dict of C{unicode} -> C{unicode}
    @type  title:       C{unicode}
    type  lookedup:     L{datetime.datetime}
    """
    chromaprint = None
    duration = None
    mbid = None
    artists = None
    title = None
    lookedup = None

    def fromResults(self, results):
        """
        Set our chromaprint from the results returned by the acoustid
        web service.
        """
        count = {}
        # lists are not hashable, sadly
        artist = {} # repr -> list


        for result in results:
            # highest-scoring result comes first ?
            recordings = result.get('recordings', [])
            for recording in recordings:
                for track in recording.get('tracks', []):
                    artists = track['artists']
                    artist[repr(artists)] = artists
                    key = (recording['id'], repr(artists), track['title'])
                    if not key in count:
                        count[key] = 0
                    count[key] += 1

        frequencies = count.items()
        ordered = sorted(frequencies, key=lambda x: -x[1])

        if not ordered:
            # no results
            return

        mbid, artists, title = ordered[0][0]

        self.artists = []
        for a in artist[artists]:
            self.artists.append({
                'name': a['name'],
                'mbid': a['id'],
            })
        self.title = title
        self.mbid = mbid


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
        self.chroma = ChromaModel()

class TrackModel(scorable.ScorableModel):
    """
    I am a model for a track.

    My controller is L{dad.controller.track.TrackController}

    @type scores:    list of L{data.Score}
    @type fragments: list of subclasses of L{FragmentModel}

    """

    # FIXME: scores ?

    # FIXME: remove fragments, use getter
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


    def getId(self):
        """
        Return the id of the model, as used by the database backend.

        @rtype: C{unicode}
        """
        raise NotImplementedError

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
        @rtype: list of L{unicode}, even if empty.
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
        return '<%s %r for %r - %r>' % (self.__class__.__name__, self.getId(),
            " & ".join(self.getArtistNames() or []),
            self.getName())

class TrackSelectorModel(selector.SelectorModel):
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

