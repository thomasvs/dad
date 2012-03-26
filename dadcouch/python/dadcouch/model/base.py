# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4


from twisted.internet import defer

from dad.model import scorable
from dad.common import log


class CouchDBModel(scorable.BackedModel, log.Loggable):
    pass


class CouchDocModel(CouchDBModel):
    """
    I represent an object in a CouchDB database that can be
    stored as a document.

    @type document: L{paisley.mapping.Document}
    """

    document = None
    documentClass = None # set by subclass

    def new(self, db, name, sort=None, mbid=None):
        """
        @type  db:   L{dadcouch.database.couch.DADDB}
        @type  name: C{unicode}
        @type  sort: C{unicode}
        @type  mbid: C{unicode}
        """
        if not sort:
            sort = name

        model = self(db)
        model.document = self.documentClass()

        model.document.name = name
        model.document.sortName = sort
        model.document.mbid = mbid
        model.document = model.document
        return model
    new = classmethod(new)

    def getUrl(self):
        return self.database.getUrl(self)
        

class ScorableModel(CouchDocModel):
    """
    I represent a subject in a CouchDB database that can be scored.
    """

    subjectType = 'none'



    def getCategories(self):
        return self.database.getCategories()

    @defer.inlineCallbacks
    def getScores(self, userName=None):
        """
        Get a subject's scores and resolve their user and category.


        @returns: L{Deferred} firing list of L{data.Score}
        """
        self.debug('Getting scores for model %r, doc %r',
            self, self.document)

        if not self.document:
            self.debug('No document, no scores')
            # import code; code.interact(local=locals())
            defer.returnValue([])
            return

        scores = yield self.database.getScores(self)
        #import code; code.interact(local=locals())
        #scores = yield self.database.getScores(self.subject)

        scores = list(scores)
        if userName:
            scores = [s for s in scores if s.user == userName]
        defer.returnValue(scores)

    def setScore(self, userName, categoryName, score):
        return self.database.setScore(self, userName, categoryName, score)

    def score(self, userName, categoryName, score):
        return self.database.score(self, userName, categoryName, score)
