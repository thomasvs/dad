# -*- Mode: Python; test_case_name: dad.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base

class TrackModel(base.Model):
    """
    I am a model for a track.

    My controller is L{dad.controller.track.TrackController}

    @ivar id:     id of the track
    @ivar scores: list of L{data.Score}
    """

    # FIXME: scores ?

    id = None

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
    
    def getName(self):
        """
        Return the name of the track, suitable for display.

        @rtype: C{unicode}
        """
        raise NotImplementedError

    def getArtists(self):
        """
        @rtype: list of C{unicode}
        """
        raise NotImplementedError

    def __repr__(self):
        return '<Track %r for %r - %r>' % (self.id, 
            " & ".join(self.getArtists() or []),
            self.getName())

