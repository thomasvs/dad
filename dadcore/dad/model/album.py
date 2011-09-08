# -*- Mode: Python; test-case-name: dad.test.test_model_album -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base
from dad.common import log

class AlbumModel(base.Model):

    """
    I am a model for an album.

    My controller is L{dad.controller.track.AlbumController}
    """
    def getName(self):
        """
        Return the name of the album, suitable for display.

        @rtype: C{unicode}
        """
        raise NotImplementedError

    def getSortName(self):
        """
        Return the name of the album, suitable for sorting.

        @rtype: C{unicode}
        """
        raise NotImplementedError


    def getTrackCount(self):
        """
        Return the number of tracks in the database by this album.
        """

    def __repr__(self):
        return '<Album %r>' % (self.getName(), )

class AlbumSelectorModel(base.Model, log.Loggable):
    """
    I am a base class for a model listing all albums in the database,
    and their track count.
    """

    logCategory = 'albumselectormodel'


    albums = None

    def get(self):
        """
        @returns: a deferred firing a list of L{dad.model.album.AlbumModel}
                  objects representing only albums and their track count.
        """
        raise NotImplementedError
