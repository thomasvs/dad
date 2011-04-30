# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import optparse

import gtk

from twisted.internet import defer
from twisted.python import failure

from dad.controller import subject
from dad.extern.log import log

from dadcouch.model import daddb
from dadcouch.model import couch
from dadcouch.selecter import couch as scouch

from dadcouch.extern.paisley import client

from dadgtk.views import track


class ArtistController(subject.SubjectController):

    @defer.inlineCallbacks
    def populate(self, subjectId, userName=None):
        yield self.populateScore(subjectId, userName)

        self.doViews('set_name', self.subject.name)

