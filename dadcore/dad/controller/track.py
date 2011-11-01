# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.python import failure

from dad.extern.log import log

from dad.controller import subject


class TrackController(subject.SubjectController):
    """
    I am a controller for a track.

    I mediate between the track model and the views on it.

    The model is a subclass of L{dad.model.track.TrackModel}
    A sample view is L{dadgtk.dadgtk.views.track.TrackView}
    """

    logCategory = 'trackcontroller'

    @defer.inlineCallbacks
    def populate(self, track, userName=None):
        yield subject.SubjectController.populate(self, track, userName)

        # FIXME: getting it again to avoid poking at internals ?
        try:
            self.debug('populating')
            artists = yield self._model.getArtistNames()
            name = yield self._model.getName()

            self.doViews('set_artist', " & ".join(artists))
            self.doViews('set_title', name)
            self.debug('populated')
        except Exception, e:
            self.warning('Exception %r', log.getExceptionMessage(e, frame=-1))
            self.warningFailure(failure.Failure(e))
            self.doViews('error', "failed to populate",
                "%r: %r" % (e, e.args))
