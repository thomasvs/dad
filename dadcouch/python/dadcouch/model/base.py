# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4


from twisted.internet import defer

from dad.model import scorable


class CouchDBModel(scorable.BackedModel):
    pass

# FIXME: split up further now for selection
# FIXME: do we need the messy klazz argument to new ?

class CouchBaseDocModel(CouchDBModel):
    """
    I represent an object in a CouchDB database that can be
    stored as a document.

    @type document: L{paisley.mapping.Document}
    """

    document = None
    documentClass = None # set by subclass

    @classmethod
    def new(cls, klazz, db):
        """
        @type  db:   L{dadcouch.database.couch.DADDB}
        """
        model = klazz(db)
        assert klazz.documentClass, '%r does not have documentClass' % klazz
        model.document = klazz.documentClass()

        return model


class CouchBackedModel(CouchBaseDocModel):
    """
    I represent an object in a CouchDB database that can be
    stored as a document.

    @type document: L{paisley.mapping.Document}
    """

    document = None
    documentClass = None # set by subclass

    @classmethod
    def new(cls, db, name, sort=None, mbid=None):
        """
        @type  db:   L{dadcouch.database.couch.DADDB}
        @type  name: C{unicode}
        @type  sort: C{unicode}
        @type  mbid: C{unicode}
        """
        model = CouchBaseDocModel.new(cls, db)
        model = super(CouchBackedModel, cls).new(cls, db)

        if not sort:
            sort = name

        model.document.name = name
        model.document.sortName = sort
        model.document.mbid = mbid
        model.document = model.document
        return model

    def getUrl(self):
        return self.database.getUrl(self)


class CouchScorableModel(CouchBackedModel):
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
