# -*- Mode: Python; test-case-name: dad.test.test_model_album -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.model import scorable, selector

class AlbumModel(scorable.ScorableModel):

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

    # FIXME: copied from artist.py; abstract ?
    @defer.inlineCallbacks
    def getMid(self):
        i = yield self.getId()
        if i:
            defer.returnValue(i)
            return

        mbid = yield self.getMbId()
        if mbid:
            defer.returnValue('album:mbid:' + mbid)
            return

        name = yield self.getName()
        if name:
            defer.returnValue('album:name:' + name)
            return

        raise KeyError


class AlbumSelectorModel(selector.SelectorModel):
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
