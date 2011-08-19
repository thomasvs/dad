# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.python import failure

from dad.extern.log import log

from dad.controller import subject


class TrackController(subject.SubjectController):

    @defer.inlineCallbacks
    def populate(self, subjectId, userName=None):
        yield self.populateScore(subjectId, userName)

        # FIXME: getting it again to avoid poking at internals ?
        try:
            self.debug('populating')
            self.doViews('set_artist', " & ".join(
                self.subject.getArtists()))
            self.doViews('set_title', self.subject.getTitle())
            self.debug('populated')
        except Exception, e:
            self.warning('Exception %r', log.getExceptionMessage(e, frame=-1))
            self.warningFailure(failure.Failure(e))
            self.doViews('error', "failed to populate",
                "%r: %r" % (e, e.args))
