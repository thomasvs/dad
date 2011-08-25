# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.python import failure

from dad.base import base

# match to scorable
# FIXME; model should not be couchdb-specific
class SubjectController(base.Controller):
    # FIXME: decide subject type
    """
    I am a controller for scorable models like
    L{dadcouch.model.daddb.ScorableModel}

    @ivar  subject: the subject this is a controller for
    """
    subject = None

    def viewAdded(self, view):
        view.connect('scored', self._scored)

    @defer.inlineCallbacks
    def _scored(self, view, category, score):
        # FIXME: user ?
        # FIXME: make interface for this model
        self.subject = yield self._model.score(
            self.subject, 'thomas', category, score)

    @defer.inlineCallbacks
    def populate(self, subjectId, userName=None):
        """
        Populate the views with the model information.

        @rtype: L{defer.Deferred}
        """
        # populate with the Track
        self.debug('populating with id %r', subjectId)
        try:
            self.subject = yield self._model.get(subjectId)
        except Exception, e:
            self.warningFailure(failure.Failure(e))
            self.doViews('error', "failed to populate",
               "%r: %r" % (e, e.args))
            defer.returnValue(None)
            return

        ret = yield self.populateScore(subjectId, userName=userName)

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def populateScore(self, subjectId, userName=None):
        assert type(subjectId) is unicode, 'subjectId %r is not unicode' % subjectId
        self.debug('populateScore(): subjectId %r', subjectId)
        # self.doViews('throb', True)

        categories = yield self._model.getCategories()
        scores = yield self._model.getScores(userName=userName)
        # scores: list of data.Score
        res = {} # category name -> score
        for category in categories:
            res[category] = None

        for couchScore in scores:
                res[couchScore.category] = couchScore.score

        for categoryName, score in res.items():
            self.debug('Calling view set_score, %r, %r', categoryName, score)
            self.doViews('set_score', categoryName, score)
