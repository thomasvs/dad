# -*- Mode: Python; test-case-name: dad.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base

class Selection(base.Model):
    """
    I am a model for a selection of tracks.
    """

    logCategory = 'selectionmodel'

    artists = None

    def get(self):
        """
        @returns: a deferred firing a generator of L{dad.model.track.TrackModel}
                  objects.
        """
        raise NotImplementedError

