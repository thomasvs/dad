# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import optparse
import time

from twisted.internet import defer

from dadcouch.extern.paisley import client, views, mapping

from dad.base import base
from dad.common import log

from dadcouch.common import manydef
from dadcouch.model import couch, lookup

# value to use for ENDKEY when looking up strings
# FIXME: something better; with unicode ?
ENDKEY_STRING = "z"

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

class ItemTracks:
    # map tracks-by-album and tracks-by-artist
    def fromDict(self, d):
        self.type = d['key'][1] # 0 for artist/album row, 1 for trackm row

        v = d['value']

        if self.type == 0:
            # artist/album row, full doc
            self.name = v['name']
            self.sortname = v.get('sortname', v['name'])
            self.id = d['id']

            # will be set in a callback to count tracks on this album
            self.tracks = 0
        else:
            # trackalbum, only track_id
            self.trackId = d['id']

class AlbumsByArtist:
    # map albums-by-artist
    def fromDict(self, d):
        self.type = d['key'][1] # 0 for artist row, 1 for album row

        v = d['value']

        if self.type == 0:
            # artist
            self.name = v['name']
            self.sortname = v.get('sortname', v['name'])
            self.id = d['id']
            self.albums = []
        else:
            # album
            self.albumId = d['id']



class DADDB(log.Loggable):
    logCategory = 'daddb'

    def __init__(self, db, dbName):
        """
        @type  db:     L{dadcouch.extern.paisley.client.CouchDB}
        @type  dbName: str
        """
        self.db = db
        self.dbName = dbName

    ### generic helper methods
    def viewDocs(self, viewName, klazz, *args, **kwargs):
        """
        Load the given view including Docs, and map to objects of the given
        klazz.
        Specify include_docs=True if you want to load full docs (and
        allow them to get cached)

        @type  db:       L{client.CouchDB}
        @type  dbName:   str
        @param klazz:    the class to instantiate objects from
        @param viewName: name of the view to load objects from
        """
        assert type(viewName) is str

        self.debug('loading %s->%r using view %r, args %r, kwargs %r',
            self.dbName, klazz, viewName, args, kwargs)

        v = views.View(self.db, self.dbName, 'dad', viewName, klazz,
            *args, **kwargs)
        d = v.queryView()

        def cb(result):
            self.debug('loaded %s->%r using view %r',
                self.dbName, klazz, viewName)
            return result
        d.addCallback(cb)

        def eb(failure):
            self.warning('Failed to query view: %r',
                log.getFailureMessage(failure))
            return failure
        d.addErrback(eb)

        return d

    def resolveIds(self, obj, idAttr, objAttr, klazz):
        """
        Resolve id's on an object into the relevant objects using the given
        klazz.

        @rtype: L{defer.Deferred}
        """
        ids = getattr(obj, idAttr)
        if not isinstance(ids, list):
            ids = [ids, ]

        res = []
        d = defer.Deferred()
        def mapped(o, res):
            res.append(o)

        for i in ids:
            d.addCallback(lambda _, j: self.db.map(self.dbName, j, klazz), i)
            d.addCallback(mapped, res)

        def done(_, res):
            ids = getattr(obj, idAttr)
            if not isinstance(ids, list):
                res = res[0]
            setattr(obj, objAttr, res)

        d.addCallback(done, res)

        d.callback(None)

        return d
            

    ### data-specific methods
    def getPlaylist(self, userName, categoryName, above, below, limit=None,
        random=False):
        """
        @type  limit:        int or None
        @type  random:       bool

        @returns: list of tracks and additional info, ordered by track id
        @rtype: L{defer.Deferred} firing
                list of Track, Slice, path, score, userId
        """
        trackDict = {} # track id -> (track, slice, path, score, userId)
        
        d = defer.Deferred()

        # seed the cache
        # FIXME: doesn't seem faster in practice
        # d.addCallback(lambda _: lookup.load(
        #    server, dbName, couch.Track, 'tracks'))
        d.addCallback(lambda _: self.viewDocs(
            'track-score', TrackScore))

        d.addCallback(lambda _: self.getTracks(
            userName, categoryName, above, below, limit=limit, random=random))
        d.addErrback(log.warningFailure, swallow=False)

        def resolveTracks(tracks):
            # tracks: list of Track, score, userId
            trackList = list(tracks)
            log.debug('playlist', 'got %r tracks', len(trackList))

            d = manydef.DeferredListSpaced()

            for track, score, userId in trackList:
                trackDict[track.id] = [track, None, None, score, userId]
                log.debug('playlist', 'track %r has score %f by user %r',
                    track, score, userId)
                d.addCallable(self.resolveIds, track,
                    'artist_ids', 'artists', couch.Artist)
                d.addCallable(self.getSlices, track)

            d.start()
            return d
        d.addCallback(resolveTracks)

        def resolveSlices(result):
            resultList = list(result)
            log.debug('playlist', 'got %r tracks sliced', len(resultList))

            d = manydef.DeferredListSpaced()

            for succeeded, result in resultList:
                if not succeeded:
                    self.warningFailure(result)
                if not result:
                    # result from resolveIds
                    continue

                slicesGen = result
                # FIXME: only keep first audiofile for now
                slice = list(slicesGen)[0]

                trackDict[slice.track_id][1] = slice

                def callable(slice, trackId):
                    d = self.getSliceFile(slice)
                    def cb(audiofile, trackId):
                        # print 'resolveSlices cb', audiofile, trackId
                        trackDict[trackId][2] = audiofile
                        return audiofile, trackId
                    d.addCallback(cb, trackId)
                    return d
                d.addCallable(callable, slice, slice.track_id)


            d.start()
            return d
        d.addCallback(resolveSlices)

        def getPaths(result):
            resultList = list(result)
            log.debug('playlist', 'got %r slices resolved', len(resultList))
            # print resultList

            dls = manydef.DeferredListSpaced()

            for succeeded, (audiofile, trackId) in resultList:
                def callable(audiofile, trackId):
                    d = self.getFilePath(audiofile)
                    def cb(path, trackId):
                        # print 'getPaths cb', audiofile, trackId
                        trackDict[trackId][2] = path
                        return trackDict[trackId]
                    d.addCallback(cb, trackId)
                    return d
                dls.addCallable(callable, audiofile, trackId)


 
            dls.start()
            return dls
        d.addCallback(getPaths)

        d.callback(None)

        return d

    def getTrack(self, userName, categoryName, above, below):
        """
        Get a single random track matching the given user's scores
        for the given category.

        @type  userName:     str
        @type  categoryName: str
        @type  above:        float
        @type  below:        float

        @rtype: L{defer.Deferred} (firing Track, score, userId)
        """
        assert type(above) is float, 'above is type %r, not float' % type(above)

        self.debug('get track for user %r in category %r between %r and %r',
            userName, categoryName, above, below)

        d = defer.Deferred()

        if userName:
            d.addCallback(lambda _: self.getUser(userName))

        def cb(user):
            d = self.getCategory(categoryName)
            d.addCallback(lambda c: self.getTrackScoresByCategory(c, user))
            return d
        d.addCallback(cb)

        d.addCallback(self.filterTrackScores, above, below)
        def cb(trackScores):
            import random
            trackScore = random.choice(trackScores)
            self.debug('picked random trackScore %r' % trackScore)

            d = self.loadTracks([trackScore, ])
            def loaded(result):
                self.debug('loaded track %r', result)

                return (result, trackScore.score, trackScore.userId)
            d.addCallback(loaded)
            return d
        d.addCallback(cb)

        d.callback(None)

        return d

    def getTracks(self, userName, categoryName, above, below, limit=None,
                  random=False):
        """
        Get all tracks matching the given user's scores for the given category.

        @type  userName:     str
        @type  categoryName: str
        @type  above:        float
        @type  below:        float
        @type  limit:        int or None
        @type  random:       bool

        @returns: list of tracks and additional info;
                  ordered by track id or randomized on request
        @rtype: L{defer.Deferred} firing list of (couch.Track, score, userId)
        """
        assert type(above) is float, 'above is type %r, not float' % type(above)

        self.debug('get tracks for user %r in category %r between %r and %r',
            userName, categoryName, above, below)

        d = defer.Deferred()

        if userName:
            d.addCallback(lambda _: self.getUser(userName))

        def cb(user):
            d = self.getCategory(categoryName)
            d.addCallback(lambda c: self.getTrackScoresByCategory(c, user))
            return d
        d.addCallback(cb)

        d.addCallback(self.filterTrackScores, above, below)
        def cb(trackScores):
            # pick limit trackScores if necessary
            kept = trackScores
            if limit:
                self.debug('Limiting trackScores to %d', limit)
                if random:
                    self.debug('Limiting randomly')
                    kept = []
                    import random as rm
                    for i in range(0, limit):
                        kept.append(rm.choice(trackScores))
                        trackScores.remove(kept[-1])
                else:
                    self.debug('Limiting first %d', limit)
                    kept = trackScores[:limit]

            self.debug('loading tracks for %r trackScores', len(kept))

            d = self.loadTracks(kept)
            def loaded(result):
                self.debug('loaded tracks for %r trackScores', len(kept))


                trackIdToScore = {}
                res = []

                for trackScore in kept:
                    trackIdToScore[trackScore.subjectId] = trackScore

                for succeeded, track in result:
                    if not succeeded:
                        log.warningFailure(track)
                    else:
                        trackScore = trackIdToScore[track.id]
                        res.append((track, trackScore.score, trackScore.userId))

                #res.sort(key=lambda r: r[0].id)
                return res
            d.addCallback(loaded)
            return d
        d.addCallback(cb)

        d.callback(None)

        return d

    def _getSingleByKey(self, viewName, objFactory, key):
        d = self.viewDocs(viewName, objFactory,
            include_docs=True, key=key)

        def cb(rows):
            l = list(rows)
            assert len(l) is 1, 'Got %r objects for key %r' % (
                len(l), key)

            obj = l[0]

            self.debug('Key %r maps to object %r', key, obj)
            return obj
        d.addCallback(cb)
        d.addErrback(log.warningFailure, swallow=False)

        return d

    def getCategory(self, categoryName):
        """
        Given a categoryName, return the L{Category} object.

        @type  categoryName: str

        @rtype: L{defer.Deferred} firing L{couch.Category}
        """
        return self._getSingleByKey('categories', couch.Category, categoryName)

    def getUser(self, userName):
        """
        Given a userName, return the L{User} object.

        @type  userName: str

        @rtype: L{defer.Deferred} firing L{couch.User}
        """
        return self._getSingleByKey('users', couch.User, userName)

    def getTrackScoresByCategory(self, category, user=None):
        """
        @rtype: L{defer.Deferred} firing list of L{TrackScore}
        """

        self.debug('Getting tracks for category %r and user %r',
            category, user)

        startkey = [category.id, ]
        endkey = [category.id, ]

        if user:
            # FIXME: id, not name!
            startkey.append(user.id)
            endkey.append(user.id + ENDKEY_STRING)
        else:
            startkey.append("")
            endkey.append(ENDKEY_STRING)

        d = self.viewDocs('track-score', TrackScore,
            include_docs=False,
            startkey=startkey, endkey=endkey)
        return d

    # filter out the track id's that don't match the score requested
    def filterTrackScores(self, trackScores, above, below):
        self.debug('filtering track scores')

        total = 0
        result = []

        for total, trackScore in enumerate(trackScores):
            if above <= trackScore.score <= below:
                result.append(trackScore)

        self.debug('kept %d of %d track scores', len(result), total)
        self.debug('first track score %r', result[0])

        return result

    def loadTracks(self, trackScores):
        d = manydef.DeferredListSpaced()

        for trackScore in list(trackScores):
            d.addCallable(self.db.map,
                self.dbName, trackScore.subjectId, couch.Track)

        d.start()

        return d

    def resolveTrack(self, track):
        """
        Given a track, resolve it to an actual slice of an audiofile.

        FIXME: for now, just return the file.
        """
        d = self.getSlices(track)

        return d

    def getSlices(self, track):
        """
        Given a track, get the slices of this track.
        """
        d = self.viewDocs('slice-lookup', couch.Slice,
            include_docs=True,
            startkey=[track.id, ""],
            endkey=[track.id, ENDKEY_STRING])

        return d

    def getSliceFile(self, slice):
        """
        Given a slice, get the audio file for this slice.
        """
        return self.db.map(self.dbName, slice.audiofile_id, couch.AudioFile)


    def getFilePath(self, file):
        """
        Return the full path of a given file.
        """
        self.log('getting path for file %r', file)
        # FIXME: file.directory_id seems unicode; does not work for url; handle
        # this in paisley internally ?
        d = self.db.map(self.dbName, str(file.directory_id), couch.Directory)

        def eb(failure, file):
            log.warningFailure(failure)
            self.warning('failure %r on file %r' % (
                log.getFailureMessage(failure), file))
            return failure

        d.addErrback(eb, file)

        def cb(obj, parts):
            # Directory has .name, Volume has .path
            if isinstance(obj, couch.Volume):
                parts.append(obj.path)
                parts.reverse()

                ret = os.path.join(*parts)
                self.log('path is %r', ret)
                return ret

            parts.append(obj.name)

            d = None

            if getattr(obj, 'parent_id', None):
                d = self.db.map(
                    self.dbName, str(obj.parent_id), couch.Directory)
            elif getattr(obj, 'volume_id', None):
                d = self.db.map(self.dbName, str(obj.volume_id), couch.Volume)

            assert d, 'child %r did not have parent path or volume' % obj

            d.addCallback(cb, parts)

            return d

            d.addCallback(cb, parts)
         
        d.addCallback(cb, [file.name, ])

        return d

class CouchDBModel(base.Model):
    def __init__(self, daddb):
        self._daddb = daddb

class ArtistSelectorModel(CouchDBModel):
    def get(self):
        """
        @returns: a deferred firing a list of L{daddb.ItemTracks} objects
                  representing only artists and their track count.
        """
        start = time.time()
        self.debug('get')
        v = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'tracks-by-artist',
            ItemTracks)
        try:
            d = v.queryView()
        except Exception, e:
            print 'THOMAS: exception', e
            return defer.fail(e)

        def cb(itemTracks):
            # convert list of ordered itemTracks of mixed type
            # into a list of only artist itemTracks with their track count
            ret = []

            artist = None

            for i in itemTracks:
                if i.type == 0:
                    artist = i
                    ret.append(artist)
                else:
                    artist.tracks += 1

            self.debug('get: got %d artists in %d seconds',
                len(ret), time.time() - start)
            return ret
        d.addCallback(cb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        return d

class AlbumSelectorModel(CouchDBModel):

    artistAlbums = None # artist id -> album ids

    def get(self):
        """
        @returns: a deferred firing a list of L{ItemTracks} objects
                  representing only albums and their track count.
        """
        self.debug('get')

        d = defer.Deferred()

        # first, load a mapping of artists to albums
        view = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'albums-by-artist',
            AlbumsByArtist)
        d.addCallback(lambda _, v: v.queryView(), view)

        def cb(items):
            self.debug('parsing albums-by-artist')
            # convert list of ordered AlbumsByArtist of mixed type
            # into a list of only album itemTracks with their track count
            artists = []

            album = None

            for i in items:
                if i.type == 0:
                    artist = i
                    artists.append(artist)
                else:
                    artist.albums.append(i)

            self.artistAlbums = {}

            for artist in artists:
                self.artistAlbums[artist.id] = [a.albumId for a in artist.albums]

            return None

        d.addCallback(cb)

        # now, load the tracks per album, and aggregate and return
        view = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'tracks-by-album',
            ItemTracks)
        d.addCallback(lambda _, v: v.queryView(), view)

        def cb(itemTracks):
            self.debug('parsing tracks-by-album')
            # convert list of ordered itemTracks of mixed type
            # into a list of only album itemTracks with their track count
            ret = []

            album = None
            for i in itemTracks:
                if i.type == 0:
                    album = i
                    ret.append(album)
                else:
                    album.tracks += 1

            return ret

        d.addCallback(cb)

        d.callback(None)

        return d

    def get_artists_albums(self, artist_ids):
        """
        @rtype: list of str
        """
        # return a list of album ids for the given list of artist ids
        # returns None if the first total row is selected, ie all artists
        ret = {}

        # first row has totals, and [None}
        if None in artist_ids:
            return None

        for artist in artist_ids:
            for album in self.artistAlbums[artist]:
                ret[album] = 1

        return ret.keys()

class TrackSelectorModel(CouchDBModel):
    # FIXME: this should actually be able to pass results in as they arrive,
    # instead of everything at the end
    def get(self):
        """
        @returns: a deferred firing a list of L{daddb.Track} objects.
        """
        d = defer.Deferred()

        self.debug('get')
        start = time.time()


        # get artists cached
        def cache(_):
            v = views.View(self._daddb.db, self._daddb.dbName,
                'dad', 'artists', couch.Artist, include_docs=True)
            return v.queryView()
        d.addCallback(cache)


        def loadTracks(artists):
            self.debug('get: %r artists cached in %d seconds',
                len(list(artists)), time.time() - start)
            v = views.View(self._daddb.db, self._daddb.dbName, 'dad', 'tracks',
                couch.Track, include_docs=True)
            try:
                d = v.queryView()
                return d
            except Exception, e:
                print 'THOMAS: exception', e
                return defer.fail(e)
        d.addCallback(loadTracks)

        def cb(tracks):
            # tracks: list of Track
            # import code; code.interact(local=locals())
            trackList = list(tracks)
            log.debug('playlist', 'got %r tracks', len(trackList))

            d = manydef.DeferredListSpaced()

            for track in trackList:
                d.addCallable(self._daddb.resolveIds, track,
                    'artist_ids', 'artists', couch.Artist)

            def trackedCb(_, tl):
                self.debug('get: %r tracks resolved in %d seconds',
                    len(list(tl)), time.time() - start)
                # import code; code.interact(local=locals())
                return tl
            d.addCallback(trackedCb, trackList)
            d.start()
            return d

        d.addCallback(cb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        d.callback(None)
        return d


