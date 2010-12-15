# -*- Mode: Python; test-case-name: dadcouch.test.test_selecter_couch -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# DAD - Digital Audio Database
# Copyright (C) 2008 Thomas Vander Stichele <thomas at apestaart dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import os
import optparse
import math
import random

from twisted.internet import defer

from dad.audio import mixing
from dad.common import log
from dad.common import selecter

from dadcouch.extern.paisley import couchdb, views, mapping
from dadcouch.common import cachedb
from dadcouch.model import couch, daddb

_DEFAULT_HOST = 'localhost'
_DEFAULT_PORT = 5984
_DEFAULT_DB = 'dad'
_DEFAULT_ABOVE = 0.7
_DEFAULT_BELOW = 1.0
_DEFAULT_CATEGORY = 'Good'

class OptionParser(selecter.OptionParser):
    standard_option_list = selecter.OptionParser.standard_option_list + [
        optparse.Option('-H', '--host',
            action="store", dest="host",
            help="CouchDB hostname (defaults to %default)",
            default=_DEFAULT_HOST),
        optparse.Option('-P', '--port',
            action="store", dest="port", type="int",
            help="CouchDB port (defaults to %default)",
            default=_DEFAULT_PORT),
        optparse.Option('-D', '--database',
            action="store", dest="database",
            help="CouchDB database name (defaults to %s)" % _DEFAULT_DB,
            default=_DEFAULT_DB),
       optparse.Option('-c', '--category',
            action="store", dest="category",
            help="category to make playlist for (defaults to %default)",
            default=_DEFAULT_CATEGORY),
        optparse.Option('-a', '--above',
            action="store", dest="above", type="float",
            help="lower bound for scores (defaults to %default)",
            default=_DEFAULT_ABOVE),
        optparse.Option('-b', '--below',
            action="store", dest="below", type="float",
            help="upper bound for scores (defaults to %default)",
            default=_DEFAULT_BELOW),
        optparse.Option('-u', '--user',
            action="store", dest="user",
            help="user"),
    ]


class CouchSelecter(selecter.Selecter, log.Loggable):
    """
    """

    option_parser_class = OptionParser

    logCategory = 'couchselecter'

    def __init__(self, options):
    #def __init__(self, dadDB, category, user,
    #    above=0.7, below=1.0, random=False, loops=-1):
        self.debug('Creating selecter, for %d loops', options.loops)
        db = cachedb.CachingCouchDB(options.host, int(options.port))
        self._dadDB = daddb.DADDB(db, 'dad')

        self._category = options.category
        self._user = options.user
        self._above = options.above
        self._below = options.below
        self._random = options.random
        self._loop = 0

        self._loops = options.loops

        self._selected = [] # list of tuple of (path, trackMix)

        self._tracks = [] # list of L{couch.Track}; private cache

    def setup(self):
        self.debug('setup')
        return self.load()

    def load(self):
        return self._loadLimited(4)

    def shuffle(self, files):
        """
        Override me for different shuffling algorithm.
        """
        res = files[:]
        random.shuffle(res)
        return res

    def _loadLimited(self, limit):
        # get a few results as fast as possible
        d = self._dadDB.getPlaylist(self._user, self._category,
            self._above, self._below, limit=limit)
        d.addCallback(self._getPlaylistCb)

        # we won't wait on this one; it's an internal deferred to get
        # all items which is slower

        self.loadDeferred = self._dadDB.getPlaylist(self._user, self._category,
            self._above, self._below)
        self.loadDeferred.addCallback(self._getPlaylistCb, resetLoad=True)
        self.debug('setting loadDef to %r', self.loadDeferred)

        return d

    def _getPlaylistCb(self, result, resetLoad=False):
        if resetLoad:
            self.debug('setting loadDef to None')
            self.loadDeferred = None

        resultList = list(result)
        log.debug('playlist', 'got %r paths resolved', len(resultList))

        for succeeded, result in resultList:
            if not succeeded:
                print result
            else:
                if result not in self._tracks:
                    self._tracks.append(result)
                    self._selected.append(result)
 

def main():
    log.init()

    parser = OptionParser()
    opts, args = parser.parse_args(sys.argv)

    selecter = CouchSelecter(opts)

    def output(result):
        track, slice, path, score, userId = result
        print path
        sys.stdout.flush()

    d = selecter.setup()
    def setupCb(_):
        log.info('main', 'Selecter set up')
        return True
    d.addCallback(setupCb)

    def startSelecting():
        # return a deferred that will be fired when we're done selecting
        selectD = defer.Deferred()

        def select(cont):
            if not cont:
                log.info('main', 'no further selecting')
                selectD.callback(None)
                return

            if cont is not True:
                # result from a previous get call
                output(cont)

            log.info('main', 'selecting')
            while False:
                log.debug('main', 'getting track now')
                track = selecter.getNow()
                if not track:
                    break

                output(track)
                sys.stdout.flush()

            log.debug('main', 'getting track later')
            d = selecter.get()
            d.addCallback(lambda r: reactor.callLater(0L, select, r))
            return d

        # trigger the chained selects
        select(True)

        return selectD

    d.addCallback(lambda _: startSelecting())

    d.addErrback(log.warningFailure)

    d.addCallback(lambda _: reactor.stop())

    # start the reactor
    from twisted.internet import reactor
    reactor.run()

if __name__ == '__main__':
    main()
