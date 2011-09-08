# -*- Mode: Python; test-case-name: dadcouch.test.test_model_daddb -*-
# vi:si:et:sw=4:sts=4:ts=4


from twisted.internet import defer

from dad.base import base
from dad.common import log


class CouchDBModel(base.Model, log.Loggable):

    def __init__(self, daddb):
        self._daddb = daddb

class CouchDocModel(CouchDBModel):
    """
    I represent an object in a CouchDB database that can be
    stored as a document.

    @type document: L{paisley.mapping.Document}
    """

    document = None

    
class ScorableModel(CouchDocModel):
    """
    I represent a subject in a CouchDB database that can be scored.
    """

    subjectType = 'none'

    def getCategories(self):
        return self._daddb.getCategories()

    @defer.inlineCallbacks
    def getScores(self, userName=None):
        """
        Get a subject's scores and resolve their user and category.

        @rtype: list of user, category, score
        """

        userId = None
        # for now, skip adding actual User docs
        # if userName:
        #     user = yield self._daddb.getOrAddUser(userName)
        #     # FIXME: unicode
        #     user.Id = unicode(user.id)

        # FIXME: the subject controller has .subject, not .track or .artist?
        subject = getattr(self, self.subjectType)
        if not subject:
            self.debug('No subject, no scores')
            import code; code.interact(local=locals())
            defer.returnValue([])
            return

        self.debug('Getting scores for %r', subject)
        scores = yield self._daddb.getScores(subject)
        #import code; code.interact(local=locals())
        #scores = yield self._daddb.getScores(self.subject)

        scores = list(scores)
        defer.returnValue(scores)

    @defer.inlineCallbacks
    def setScore(self, subject, userName, categoryName, score):
        doc = getattr(subject, self.subjectType)
        doc = yield self._daddb.score(doc, userName, categoryName, score)
        setattr(subject, self.subjectType, doc)
        defer.returnValue(subject)
