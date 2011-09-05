# -*- Mode: Python; test_case_name: dad.test.test_model_artist -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.base import base
from dad.common import log

class ArtistModel(base.ScorableModel):

    """
    I am a model for an artist.

    My controller is L{dad.controller.track.ArtistController}
    """
    def getName(self):
        """
        Return the name of the artist, suitable for display.

        @rtype: L{twisted.internet.defer.Deferred} firing C{unicode}
        """
        raise NotImplementedError

    def setName(self, name):
        """
        Set the name of the artist, suitable for display.

        @type  name: C{unicode}

        @rtype: L{twisted.internet.defer.Deferred} firing C{None}
        """
        raise NotImplementedError

    def getSortName(self):
        """
        Return the name of the artist, suitable for sorting.

        @rtype: L{twisted.internet.defer.Deferred} firing C{unicode}
        """
        raise NotImplementedError

    def getMbId(self):
        """
        Return the MusicBrainz id of the artist.

        @rtype: L{twisted.internet.defer.Deferred} firing C{unicode}
        """
        raise NotImplementedError


    def getTrackCount(self):
        """
        Return the number of tracks in the database by this artist.

        @rtype: L{twisted.internet.defer.Deferred} firing C{int}
        """

    @defer.inlineCallbacks
    def getMid(self):
        i = yield self.getId()
        if i:
            defer.returnValue(i)
            return

        mbid = yield self.getMbId()
        if mbid:
            defer.returnValue('artist:mbid:' + mbid)
            return

        name = yield self.getName()
        if name:
            defer.returnValue('artist:name:' + name)
            return

        raise KeyError

    def save(self):
        """
        Save the model to the database backend.

        @rtype: L{twisted.internet.defer.Deferred} firing L{ArtistModel}
        """

    def __repr__(self):
        return '<ArtistModel %r>' % (self.getName(), )

class ArtistSelectorModel(base.Model, log.Loggable):
    """
    I am a base class for a model listing all artists in the database,
    and their track count.
    """

    logCategory = 'artistselectormodel'


    artists = None

    def get(self):
        """
        @returns: a deferred firing a list of L{dad.model.artist.ArtistModel}
                  objects representing only artists and their track count.
        """
        raise NotImplementedError
