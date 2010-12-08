# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import optparse

from twisted.internet import defer

from dad.extern.paisley import couchdb, views, mapping

from dad.common import log, manydef
from dad.model import couch, lookup, daddb

# FIXME: an alternative to DeferredList where we add callables returning
# deferreds and they get executed serially by chaining them one after another

class DeferredSerial:
    def __init__(self):
        self._results = [] # list of SUCCESS/FAILURE, result
        self._d = defer.Deferred()

    def addCallable(self, callable, *args, **kwargs):
        self._d.addCallback(callable, *args, **kwargs)
        def cb(result):
            self._results.append((defer.SUCCESS, result))
            return result
        self._d.addCallback(cb)
        def eb(failure):
            self._results.append((defer.FAILURE, failure))
            return failure
        self._d.addErrback(eb)

    def callback(self, result):
        # call the first deferred with the given result
        def cb(result):
            return self._results
        self._d.addCallback(cb)

        self._d.callback(result)

    def gatherResults(self):
        return self._d

# map track-score view
class TrackScore(mapping.Document):
    categoryId = mapping.TextField()
    userId = mapping.TextField()
    subjectId = mapping.TextField()
    score = mapping.FloatField()

    def fromDict(self, d):
        self.categoryId = d['key'][0]
        self.userId = d['key'][1]
        self.subjectId = d['key'][2]
        self.score = float(d['value'])



def main():
    log.init()

    parser = optparse.OptionParser()

    parser.add_option('-c', '--category',
        action="store", dest="category",
        help="category to make playlist for",
        default="Good")

    parser.add_option('-a', '--above',
        action="store", dest="above",
        help="lower bound for scores",
        default="0.7")
    parser.add_option('-b', '--below',
        action="store", dest="below",
        help="upper bound for scores",
        default="1.0")

    parser.add_option('-l', '--limit',
        action="store", dest="limit",
        help="limit number of items",
        default=None)

    parser.add_option('-u', '--user',
        action="store", dest="user",
        help="user")



    opts, args = parser.parse_args(sys.argv)

    serverName = 'localhost'
    if len(args) > 1:
        serverName = args[1]

    dbName = 'dad'
    if len(args) > 2:
        dbName = args[2]

    # this rebinds and makes it break in views
    # db = couchdb.CouchDB('localhost', dbName='dad')
    server = couchdb.CouchDB(serverName)
    dadDB = daddb.DADDB(server, dbName)

    d = dadDB.getPlaylist(opts.user, opts.category,
        float(opts.above), float(opts.below),
        limit=opts.limit and int(opts.limit) or None)

    def showPaths(result):
        resultList = list(result)
        log.debug('playlist', 'got %r paths resolved', len(resultList))

        for succeeded, result in resultList:
            if not succeeded:
                print 'ERROR', result
            else:
                (track, slice, path, score, userId) = result
                print path.encode('utf-8')

    d.addCallback(showPaths)

    # stop at the end
    d.addCallback(lambda _: reactor.stop())
    d.addErrback(log.warningFailure, swallow=False)
    d.addErrback(lambda _: reactor.stop())

    return d

from twisted.internet import reactor

reactor.callLater(0, main)
reactor.run()

