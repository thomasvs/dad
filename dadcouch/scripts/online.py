# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# check consistency of the database by making sure all document id's are
# present and correct


import os
import sys
import time

from twisted.internet import defer

from dad.extern.paisley import couchdb, views, mapping

from dad.model import couch, lookup, daddb
from dad.common import log, manydef, cachedb

def isFileOnline(dadDB, file):
    log.log('check', 'is file %r online ?' % file)
    d = dadDB.getFilePath(file)

    def cb(path):
        log.log('check', 'statting path %r', path)
        # nfs can make these calls take long
        before = time.time()
        res = os.path.exists(path)
        if time.time() - before > 2.0:
            log.warning('check', 'slow filesystem for %r' % path)
        
        if res:
            return True

        print "%s offline" % path.encode('utf-8')

    d.addCallback(cb)
    return d

def isSliceOnline(dadDB, slice):
    log.log('check', 'is slice %r online ?' % slice)
    d = dadDB.db.map(dadDB.dbName, str(slice.audiofile_id), couch.AudioFile)
    d.addCallback(lambda f: isFileOnline(dadDB, f))
    return d

def isAnySliceOnline(dadDB, slices):
    log.log('check', 'is any of slices %r online ?' % slices)
    dl = []
    for s in slices:
        dl.append(isSliceOnline(dadDB, s))

    d = defer.DeferredList(dl)
    def consolidate(results):
        for succeeded, result in results:
            if result is True:
                return True

        return False
    d.addCallback(consolidate)

    return d

def audiofiles(dadDB):
    d = dadDB.viewDocs('audiofile-lookup', couch.AudioFile, include_docs=True)

    def load(res):
        res = list(res)

        d = manydef.DeferredListSpaced()

        for audiofile in res:
            log.log('check', 'adding online check for audiofile %r', audiofile)
            d.addCallable(isFileOnline, dadDB, audiofile)

        def count(_):
            total = 0
            errors = 0
            online = 0
            for succeeded, result in d.resultList:
                total += 1
                if not succeeded:
                    errors += 1
                else:
                    if result:
                        online += 1

            print "%d of %d audiofiles online" % (online, total)
            if errors:
                print "%d errors" % errors

            log.info('online', "%d cache hits of %d lookups",
                dadDB.db.hits, dadDB.db.lookups)

        d.addCallback(count)

        d.start()

        return d

    d.addCallback(load)

    return d

def slices(dadDB):
    """
    @type db:     L{couchdb.CouchDB}
    @type dbName: str
    """
    d = dadDB.viewDocs('slice-lookup', couch.Slice, include_docs=True)

    def load(res):
        res = list(res)
        log.debug('slices', 'loaded %d slices', len(res))

        d = manydef.DeferredListSpaced()

        for slice in res:
            log.log('check', 'adding online check for slice %r', slice)
            d.addCallable(isSliceOnline, dadDB, slice)

        def count(_):
            total = 0
            errors = 0
            online = 0
            for succeeded, result in d.resultList:
                total += 1
                if not succeeded:
                    errors += 1
                else:
                    if result:
                        online += 1

            print "%d of %d slices online" % (online, total)
            if errors:
                print "%d errors" % errors

            log.info('online', "%d cache hits of %d lookups",
                dadDB.db.hits, dadDB.db.lookups)

        
        d.addCallback(count)

        log.debug('online', "counting online slices")
        d.start()

        return d

    d.addCallback(load)

    return d

def tracks(dadDB):
    """
    @type db:     L{couchdb.CouchDB}
    @type dbName: str
    """
    # slices point to tracks, so load slices first to build a map
    track_ids = {} # track_id -> list of Slice

    d = dadDB.viewDocs('slice-lookup', couch.Slice, include_docs=True)

    # map tracks to slices
    def slicesLoadedCb(slices):
        for slice in slices:
            if slice.track_id not in track_ids:
                track_ids[slice.track_id] = []

            track_ids[slice.track_id].append(slice)
    d.addCallback(slicesLoadedCb)

    # load tracks
    d.addCallback(lambda _: dadDB.viewDocs(
        'tracks', couch.Track, include_docs=True))

    def trackLoadedCb(tracks):
        tracks = list(tracks)
        log.debug('tracks', 'loaded %d tracks', len(tracks))

        d = manydef.DeferredListSpaced()

        for track in tracks:
            log.log('tracks', 'adding online check for track %r', track)
            if track.id not in track_ids:
                # no slices referencing this track, so offline
                log.log('tracks', 'Track %r has 0 slices', track)
                d.addCallable(lambda: False)
            else:
                if len(track_ids[track.id]) > 1:
                    log.debug('tracks',
                        "Track %r has %d slices" % (
                            track, len(track_ids[track.id])))

                d.addCallable(isAnySliceOnline, dadDB, track_ids[track.id])

        log.debug('tracks', 'checking offline tracks')
        def count(resultList):
            log.debug('tracks', 'counting offline tracks out of %r total',
                len(resultList))
            total = len(resultList)
            online = 0

            for i, (succeeded, result) in enumerate(resultList):
                if result:
                    online += 1
                else:
                    print "track %r offline" % tracks[i]

            print "%d of %d tracks online" % (online, total)

            log.info('online', "%d cache hits of %d lookups",
                dadDB.db.hits, dadDB.db.lookups)

        d.addCallback(count)

        d.start()
        return d

    d.addCallback(trackLoadedCb)
    return d

def main():
    log.init()
    server = 'localhost'
    if len(sys.argv) > 1:
        server = sys.argv[1]

    dbName = 'dad'
    if len(sys.argv) > 2:
        dbName = sys.argv[2]

    # this rebinds and makes it break in views
    # db = couchdb.CouchDB('localhost', dbName='dad')
    db = cachedb.CachingCouchDB(server)
    dadDB = daddb.DADDB(db, dbName)

    d = defer.Deferred()
    
    # get Volume and Directory into the cache so that we don't do a lot
    # of parallel lookups for them
    d.addCallback(lambda _: dadDB.viewDocs(
        'directory-lookup', couch.Directory, include_docs=True))
    d.addCallback(lambda _: log.debug('online', '%d directories', len(list(_))))
    d.addCallback(lambda _: dadDB.viewDocs(
        'volumes', couch.Volume, include_docs=True))
    d.addCallback(lambda _: log.debug('online', '%d volumes', len(list(_))))

    # now check stuff
    # audiofiles first, so we seed the cache before checking tracks
    d.addCallback(lambda _: audiofiles(dadDB))
    d.addCallback(lambda _: tracks(dadDB))
    d.addCallback(lambda _: slices(dadDB))

    d.addCallback(lambda _: reactor.stop())

    def eb(f):
        print 'ERROR: ', log.getFailureMessage(f)
        reactor.stop()
    d.addErrback(eb)

    d.callback(None)
    return d

from twisted.internet import reactor

reactor.callLater(0, main)
reactor.run()

