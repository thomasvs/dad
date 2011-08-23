# -*- Mode: Python; test_case_name: dad.test.test_model_track -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base

class ArtistModel(base.Model):
    """
    I am a model for an artist.

    My controller is L{dad.controller.track.ArtistController}
    """
    def getName(self):
        """
        Return the name of the artist, suitable for display.

        @rtype: C{unicode}
        """
        raise NotImplementedError

    def getSortName(self):
        """
        Return the name of the artist, suitable for sorting.

        @rtype: C{unicode}
        """
        raise NotImplementedError


    def getTrackCount(self):
        """
        Return the number of tracks in the database by this artist.
        """

    def __repr__(self):
        return '<Artist %r>' % (self.getName(), )

class ArtistSelectorModel(base.Model):
    """
    I am a base class for a model listing all artists in the database,
    and their track count.
    """

    artists = None

    def get(self):
        """
        @returns: a deferred firing a list of L{ArtistModel} objects
                  representing only artists and their track count.
        """
        raise NotImplementedError
