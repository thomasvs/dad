# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# check consistency of the database by making sure all document id's are
# present and correct


import os
import sys

from twisted.internet import defer

from dad.extern.paisley import couchdb, views, mapping
from dad.common import log


from dad.model import couch, lookup

# possibly turn into a class and allow setting up verification before
# executing, so we can launch the view queries at almost the same moment
# to get as consistent a view as possible
def verify(db, dbName,
           sourceKlazz, sourceView, attribute,
           destKlazz, destView, cache=None):
    """
    Verify that all references from the given source documents resolve to
    existing references to the given destination documents through a given
    attribute name.

    @type  db:          L{couchdb.CouchDB}
    @type  dbName:      str
    @param sourceKlazz: the source class to instantiate objects from
    @param sourceView:  name of the source view to load objects from
    @param attribute:   name of the attribute on source objects to resolve
                        through.  The attribute can be a single id or a list.
    @type  attribute:   str
    @param destKlazz:   the destination class to instantiate objects from
    @param destView:    name of the destination view to load objects from
    @type  cache:       dict of class -> dict of id -> object
    """
    log.debug('consistency',
        'verify: sourceKlazz %r, attribute %r, destKlazz %r',
        sourceKlazz, attribute, destKlazz)

    if cache is None:
        cache = {}

    d = defer.Deferred()

    d.addCallback(lambda _:
        lookup.cacheLoad(cache, db, dbName, sourceKlazz, sourceView))
    d.addCallback(lambda _:
        lookup.cacheLoad(cache, db, dbName, destKlazz, destView))

    def cb(_):
        log.debug('consistency',
            'got objects for %r and %r', sourceKlazz, destKlazz)
        errors = 0
        items = 0

        isList = False
        attr = getattr(sourceKlazz, attribute)
        if isinstance(attr, mapping.ListField):
            isList = True

        values = cache[sourceKlazz].values()
        log.debug('consistency', 'got %d items for %r',
            len(values), sourceKlazz)

        for item in values:
            log.log('consistency', 'item %r', item)
            values = getattr(item, attribute)
            if not isList:
                values = [getattr(item, attribute), ]

            log.log('consistency', 'values %r', values)

            for item_id in values:
                # allow None/unset id's
                if item_id is None:
                    continue

                if item_id not in cache[destKlazz].keys():
                    print '%r %r has %r %r but does not exist' % (
                        sourceKlazz, item.id, destKlazz, item_id)
                    import code;code.interact(local=locals())
                    errors += 1
                    if cache[destKlazz][item_id].type != sourceKlazz.type:
                        print '%r %r points to %r %r but type is %r' % (
                            sourceKlazz, item.id, destKlazz, item_id,
                            cache[destKlazz][item_id].type)
                else:
                    items += 1

        if errors == 0:
            print '%s.%s is consistent (%d items)' % (
                sourceKlazz.__name__, attribute, items)

    def eb(failure):
        log.warningFailure(failure)
        print 'ERROR: could not verify %s.%s: %r' % (
            sourceKlazz.__name__, attribute, failure)

    d.addCallback(cb)
    d.addErrback(eb)

    d.callback(None)
    return d

def check(db, dbName):
    """
    @type db:     L{couchdb.CouchDB}
    @type dbName: str
    """
    # loads each 'table' into a dict of id -> object
    cache = {} # class -> all docs of that class
    d = defer.Deferred()


    d.addCallback(lambda _: verify(db, dbName,
        couch.Directory, 'directory-lookup', 'volume_id',
        couch.Volume, 'volumes', cache=cache))
    d.addCallback(lambda _: verify(db, dbName,
        couch.Directory, 'directory-lookup', 'parent_id',
        couch.Directory, 'directory-lookup', cache=cache))

    d.addCallback(lambda _: verify(db, dbName,
        couch.AudioFile, 'audiofile-lookup', 'directory_id',
        couch.Directory, 'directory-lookup', cache=cache))

    d.addCallback(lambda _: verify(db, dbName,
        couch.Slice, 'slice-lookup', 'track_id',
        couch.Track, 'tracks', cache=cache))

    d.addCallback(lambda _: verify(db, dbName,
        couch.Album, 'albums', 'artist_ids',
        couch.Artist, 'artists', cache=cache))

    d.addCallback(lambda _: verify(db, dbName,
        couch.Track, 'tracks', 'artist_ids',
        couch.Artist, 'artists', cache=cache))

    d.addCallback(lambda _: verify(db, dbName,
        couch.TrackAlbum, 'trackalbum-lookup', 'album_id',
        couch.Album, 'albums', cache=cache))
    d.addCallback(lambda _: verify(db, dbName,
        couch.TrackAlbum, 'trackalbum-lookup', 'track_id',
        couch.Track, 'tracks', cache=cache))

    d.callback(None)

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
    log.debug('main', 'binding to couchdb %r', server)
    db = couchdb.CouchDB(server)
    log.debug('main', 'checking database %r', dbName)
    d = check(db, dbName)
    d.addCallback(lambda _: reactor.stop())
    return d

from twisted.internet import reactor

reactor.callLater(0, main)
reactor.run()

