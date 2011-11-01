# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.controller import subject


class ArtistController(subject.SubjectController):
    """
    I am a controller for an artist.

    I mediate between the artist model and the views on it.

    The model is a subclass of L{dad.model.artist.ArtistModel}
    """

    @defer.inlineCallbacks
    def populate(self, artist, userName=None):
        yield subject.SubjectController.populate(
            self, artist, userName)

        name = yield self._model.getName()
        self.doViews('set_name', name)
