# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import optparse

import gtk

from twisted.internet import defer
from twisted.python import failure

from dad.base import base
from dad.extern.log import log

from dadcouch.model import daddb
from dadcouch.model import couch
from dadcouch.selecter import couch as scouch

from dadcouch.extern.paisley import client

from dadgtk.views import track


# match to scorable
class SubjectController(base.Controller):

    subject = None

    # FIXME: push to base class
    def __init__(self, model):
        base.Controller.__init__(self, model)

    def viewAdded(self, view):
        view.connect('scored', self._scored)

    def _scored(self, view, category, score):
        print 'THOMAS: scored', category, score
        # FIXME: user ?
        # FIXME: make interface for this model
        self._model.score(self.subject, 'thomas', category, score)

    def populate(self, subjectId, userName=None):
        return self.populateScore(subjectId, username)

    @defer.inlineCallbacks
    def populateScore(self, subjectId, userName=None):
        assert type(subjectId) is unicode, 'subjectId %r is not unicode' % subjectId
        self.debug('populateScore(): subjectId %r', subjectId)
        # self.doViews('throb', True)

        # populate with the Track
        try:
            self.subject = yield self._model.get(subjectId)
        except Exception, e:
            self.warningFailure(failure.Failure(e))
            self.doViews('error', "failed to populate",
                "%r: %r" % (e, e.args))

        categories = yield self._model.getCategories()
        scores = yield self._model.getScores(userName=userName)
        # scores: list of couch.Score with resolutions
        res = {} # category name -> score
        for category in categories:
            res[category.name] = None

        for couchScore in scores:
            for scoreDict in couchScore.scores:
                # scoreDict is DictField of category_id/score/category
                # FIXME: user
                res[scoreDict['category'].name] = scoreDict['score']

        for categoryName, score in res.items():
            self.doViews('set_score', categoryName, score)
