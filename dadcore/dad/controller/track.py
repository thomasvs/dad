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


class TrackController(base.Controller):

    _track = None

    # FIXME: push to base class
    def __init__(self, model):
        base.Controller.__init__(self, model)

    def viewAdded(self, view):
        view.connect('scored', self._scored)

    
    def _scored(self, view, category, score):
        print 'THOMAS: scored', category, score
        # FIXME: user ?
        # FIXME: make interface for this model
        self._model.score(self._track, 'thomas', category, score)

    @defer.inlineCallbacks
    def populate(self, trackId, userName=None):
        assert type(trackId) is unicode, 'trackId %r is not unicode' % trackId
        self.debug('populate(): trackId %r', trackId)
        # self.doViews('throb', True)

        # populate with the Track
        try:
            self._track = yield self._model.get(trackId)

            self.debug('populating')
            self.doViews('set_artist', " & ".join(
                [a.name for a in self._track.artists]))
            self.doViews('set_title', self._track.name)
            self.debug('populated')
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
