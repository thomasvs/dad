# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.controller import subject


class AlbumController(subject.SubjectController):

    @defer.inlineCallbacks
    def populate(self, album, userName=None):
        yield subject.SubjectController.populate(
            self, album, userName)

        name = yield self._model.getName()
        self.doViews('set_name', name)
