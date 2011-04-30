# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.python import failure

from dad.controller import subject


class TrackController(subject.SubjectController):

    @defer.inlineCallbacks
    def populate(self, subjectId, userName=None):
        yield self.populateScore(subjectId, userName)

        # FIXME: getting it again to avoid poking at internals ?
        try:
            self.debug('populating')
            self.doViews('set_artist', " & ".join(
                [a.name for a in self.subject.artists]))
            self.doViews('set_title', self.subject.name)
            self.debug('populated')
        except Exception, e:
            self.warningFailure(failure.Failure(e))
            self.doViews('error', "failed to populate",
                "%r: %r" % (e, e.args))
