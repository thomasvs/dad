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

    def addFragment(self, info, metadata=None, mix=None, number=None):
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

