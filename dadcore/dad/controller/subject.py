# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer
from twisted.python import failure

from dad.base import base

# match to scorable
# FIXME; model should not be couchdb-specific
# FIXME: subject and self._model are the same here ?
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
    def populate(self, subject, userName=None):
        """
        Populate the views with the model information.

        @type  subject: subclass of L{dad.model.base.ScorableModel}

        @rtype: L{defer.Deferred}
        """
        # populate with the Subject
        self.debug('populating with subject %r', subject)
        mid = yield subject.getMid()
        try:
            self.subject = yield self._model.get(mid)
        except IndexError:
            self.debug('No item for subject %r', subject)

        ret = yield self.populateScore(self.subject, userName=userName)

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def populateScore(self, subjectId, userName=None):
        # assert type(subjectId) is unicode, 'subjectId %r is not unicode' % subjectId
        self.debug('populateScore(): subjectId %r', subjectId)
        # self.doViews('throb', True)

        categories = yield self.subject.getCategories()
        scores = yield self.subject.getScores(userName=userName)
        # scores: list of data.Score
        res = {} # category name -> score
        for category in categories:
            res[category] = None

        for couchScore in scores:
                res[couchScore.category] = couchScore.score

        for categoryName, score in res.items():
            self.debug('Calling view set_score, %r, %r', categoryName, score)
            self.doViews('set_score', categoryName, score)
