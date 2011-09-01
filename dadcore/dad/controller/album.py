# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.controller import subject


class AlbumController(subject.SubjectController):

    @defer.inlineCallbacks
    def populate(self, album, userName=None):
        yield self.populateScore(album, userName)

        name = yield self.subject.getName()
        self.doViews('set_name', name)
