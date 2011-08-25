# -*- Mode: Python; test_case_name: dadcouch.test.test_model_daddb -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import time

from twisted.internet import defer

from zope import interface

from dadcouch.extern.paisley import mapping
from dadcouch.extern.paisley import views

from dad import idad
from dad.base import base, data
from dad.common import log
from dad.model import artist

from dadcouch.common import manydef
from dadcouch.model import couch

# value to use for ENDKEY when looking up strings
# FIXME: something better; with unicode ?
ENDKEY_STRING = "z"

# generic row mapping, with id
class GenericIdRow:
    def fromDict(self, d):
        self.id = d['id']
        self.key = d['key']
        self.value = d['value']

class GenericRow:
    def fromDict(self, d):
        self.key = d['key']
        self.value = d['value']


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

# map track view
class TrackRow(mapping.Document):
    id = mapping.TextField()
    name = mapping.TextField()
    artist_ids = mapping.ListField(mapping.TextField())

    artist = mapping.DictField(mapping.Mapping.build(
            name = mapping.TextField(),
            sortname = mapping.TextField(),
            id = mapping.TextField(),
    ))
 
    def fromDict(self, d):
        self.id = d['id']
        self.name = d['key']
        self.artists = d['value']

# map score view results
class ScoreRow(mapping.Document):
    id = mapping.TextField()
    user = mapping.TextField()
    category = mapping.TextField()
    score = mapping.FloatField()

    def fromDict(self, d):
        self.id = d['id']
        self.name = d['key']
        self.user, self.category, self.score = d['value']


# FIXME: rename
class ItemTracksByArtist(artist.ArtistModel):

    tracks = 0 # int
    id = None
    trackId = None

    # map tracks-by-artist
    def fromDict(self, d):
        self.name, self.sortname, self.id = d['key']

        self.trackId = d['value']

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def getSortName(self):
        return self.sortname

    def getTrackCount(self):
        return self.tracks
    
class ItemAlbumsByArtist:

    tracks = 0 # int
    artistName = None
    artistSortname = None
    artistId = None

    # of album
    name = None
    sortname = None
    id = None

    # map view-albums-by-artist
    # key: artist name, sortname, id; album name, sortname, id
    # value: track count
    def fromDict(self, d):
        self.artistName, self.artistSortname, self.artistId, self.name, self.sortname, self.id = d['key']

        self.tracks = d['value']


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
    """
    @type  db:     L{dadcouch.extern.paisley.client.CouchDB}
    @type  dbName: str
    """

    interface.implements(idad.IDatabase)

    logCategory = 'daddb'

    def __init__(self, db, dbName):
        """
        @type  db:     L{dadcouch.extern.paisley.client.CouchDB}
        @type  dbName: str
        """
        self.db = db
        self.dbName = dbName

        self.debug('My FUTON is at http://%s:%d/_utils/index.html',
            self.db.host, self.db.port)

    ### generic helper methods

    # FIXME: work around having to poke at doc._data
    def saveDoc(self, doc, docId=None):
        return self.db.saveDoc(self.dbName, doc._data, docId=docId)

    def viewDocs(self, viewName, klazz, *args, **kwargs):
        """
        Load the given view including Docs, and map to objects of the given
        klazz.
        Specify include_docs=True if you want to load full docs (and
        allow them to get cached)

        @param viewName: name of the view to load objects from
        @param klazz:    the class to instantiate objects from
        """
        assert type(viewName) is str

        self.debug('loading %s->%r using view %r, args %r, kwargs %r',
            self.dbName, klazz, viewName, args, kwargs)
        self.doLog(log.DEBUG, where=-2, format='loading for')

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
            sys.stderr.write(failure.getTraceback())
            return failure
        d.addErrback(eb)

        return d

    # FIXME: move this method to paisley
    def resolveIds(self, obj, idAttr, objAttr, klazz, getter=getattr, setter=setattr):
        """
        Resolve id's on an object into the relevant objects using the given
        klazz.

        @rtype: L{defer.Deferred} firing obj, so it can be chained.
        """
        ids = getter(obj, idAttr)

        if not isinstance(ids, list):
            ids = [ids, ]

        res = []
        d = defer.Deferred()
        def mapped(o, res):
            res.append(o)

        for i in ids:
            # FIXME: again, unicode!
            i = unicode(i)
            d.addCallback(lambda _, j: self.db.map(self.dbName, j, klazz), i)
            d.addCallback(mapped, res)

        def done(_, r):
            ids = getter(obj, idAttr)
            if not isinstance(ids, list):
                r = r[0]
            setter(obj, objAttr, r)

            return obj

        d.addCallback(done, res)

        d.callback(None)

        return d
            
    def resolveDictIds(self, obj, idAttr, objAttr, klazz,
            getter=getattr, setter=setattr):
        return self.resolveIds(obj, idAttr, objAttr, klazz,
            getter=dict.__getitem__, setter=dict.__setitem__)

    ### data-specific methods

    ## idad.IDatabase interface
    def new(self):
        return couch.Track()

    @defer.inlineCallbacks
    def save(self, track):
        stored = yield self.saveDoc(track)
        # FIXME: for now, look it up again to maintain the track illusion
        track = yield self.db.map(self.dbName, stored['id'], couch.Track)
        defer.returnValue(track)

    @defer.inlineCallbacks
    def getTracks(self):
        ret = yield self.viewDocs('view-tracks-title', couch.Track,
            include_docs=True)

        defer.returnValue(list(ret))


    @defer.inlineCallbacks
    def getCategories(self):
        rows = yield self.viewDocs('view-categories', GenericRow,
            group_level=1)
        rows = list(rows)
        categories = [row.key for row in rows]
        defer.returnValue(categories)

    @defer.inlineCallbacks
    def getScores(self, subject):
        """
        @returns: deferred firing list of L{data.Score}
        """

        # get all scores for this subject
        rows = yield self.viewDocs('view-scores-by-subject', ScoreRow,
            key=subject.id)

        rows = list(rows)

        if not rows:
            self.debug('No scores for %r', subject)
            defer.returnValue([])
            return

        scores = []
        for row in rows:
            score = data.Score()
            score.subject = subject
            score.user = row.user
            score.category = row.category
            score.score = row.score
            scores.append(score)

        self.debug('%d scores for %r', len(scores), subject.id)
        defer.returnValue(scores)

    @defer.inlineCallbacks
    def getTracksByHostPath(self, host, path):
        """
        Look up tracks by path.
        Can return multiple tracks for a path; for example, multiple
        fragments.


        @type  host: unicode
        @type  path: unicode

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{couch.Track}
        """
        assert type(host) is unicode, \
            'host is type %r, not unicode' % type(host)
        assert type(path) is unicode, \
            'host is type %r, not unicode' % type(path)

        self.debug('get track for host %r and path %r', host, path)

        ret = yield self.viewDocs('view-host-path', couch.Track,
            include_docs=True, key=[host, path])

        defer.returnValue(ret)

    def trackAddFragment(self, track, info, metadata=None, mix=None, number=None):
        return track.addFragment(info, metadata, mix, number)

    @defer.inlineCallbacks
    def getTracksByMD5Sum(self, md5sum):
        """
        Look up tracks by md5sum
        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{couch.Track}
        """
        self.debug('get track for md5sum %r', md5sum)

        ret = yield self.viewDocs('view-md5sum', couch.Track,
            include_docs=True, key=md5sum)

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def getTracksByMBTrackId(self, mbTrackId):
        """
        Look up tracks by musicbrainz track id.

        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{couch.Track}
        """
        self.debug('get track for mb track id %r', mbTrackId)

        ret = yield self.viewDocs('view-mbtrackid', couch.Track,
            include_docs=True, key=mbTrackId)

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def trackAddFragmentFileByMD5Sum(self, track, info, metadata=None, mix=None, number=None):
        """
        Add the given file to each fragment with a file with the same md5sum.
        """
        self.debug('get track for track %r', track.id)

        track = yield self.db.map(self.dbName, track.id, couch.Track)

        # FIXME: possibly raise if we don't find it ?
        found = False

        for fragment in track.fragments:
            for f in fragment.files:
                if f.md5sum == info.md5sum:
                    self.debug('Appending to fragment %r', fragment)
                    track.filesAppend(fragment.files, info, metadata, number)
                    self.debug('fragment %r now has %r files', fragment,
                        len(fragment.files))
                    found = True
                    break
            if found:
                break

        track = yield self.save(track)
        defer.returnValue(track)

    @defer.inlineCallbacks
    def trackAddFragmentFileByMBTrackId(self, track, info, metadata, mix=None, number=None):
        self.debug('get track for track id %r', track.id)

        track = yield self.db.map(self.dbName, track.id, couch.Track)

        # FIXME: possibly raise if we don't find it ?
        found = False

        if len(track.fragments) > 1:
            self.warning('Not yet implemented finding the right fragment to add by mbid')

        for fragment in track.fragments:
            for f in fragment.files:
                if f.metadata and f.metadata.mb_track_id == metadata.mbTrackId:
                    self.debug('Appending to fragment %r', fragment)
                    track.filesAppend(fragment.files, info, metadata, number)
                    found = True
                    break
            if found:
                break

        stored = yield self.saveDoc(track)

        track = yield self.db.map(self.dbName, stored['id'], couch.Track)
        defer.returnValue(track)

    @defer.inlineCallbacks
    def score(self, subject, userName, categoryName, score):
        # FIXME: maybe we should first get the most recent version,
        #        then update, to avoid conflicts ?
        self.debug('asked to score subject %r '
            'for user %r and category %r to score %r',
            subject, userName, categoryName, score)

        found = False
        ret = None

        for i, s in enumerate(subject.scores):
            if s.user == userName and s.category == categoryName:
                self.debug('Updating score for %r in %r from %r to %r',
                    userName, categoryName, s.score, score)
                subject.scores[i].score = score
                ret = yield self.save(subject)
                found = True

        if not found:
            self.debug('Setting score for %r in %r to %r',
                userName, categoryName, score)
            if not subject.scores:
                subject.scores = []
            subject.scores.append({
                'user': userName,
                'category': categoryName,
                'score': score
            })
            ret = yield self.save(subject)

        defer.returnValue(ret)

### FIXME: old methods that should be reworked
class NoWayJose:
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
            # returns: a deferred firing a list of
            # (result, Track/sliceGen alternating

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
                if isinstance(result, couch.Track):
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

            d = self.loadTracksFromTrackScores([trackScore, ])
            def loaded(result):
                result = list(result)
                assert len(result) == 1
                success, track = result[0]
                assert success
                self.debug('loaded track %r', track)

                return (track, trackScore.score, trackScore.userId)
            d.addCallback(loaded)
            return d
        d.addCallback(cb)

        d.callback(None)

        return d

    # FIXME: new method in interface, no params
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

            d = self.loadTracksFromTrackScores(kept)
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
                if random:
                    import random as rm
                    rm.shuffle(res)

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
            if len(l) == 0:
                raise KeyError("No object for key %r in view %r" % (
                    key, viewName))

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

    def getCategories(self):
        return self.viewDocs('categories', couch.Category, include_docs=True)

    def getUser(self, userName):
        """
        Given a userName, return the L{User} object.

        @type  userName: str

        @rtype: L{defer.Deferred} firing L{couch.User}
        """
        return self._getSingleByKey('users', couch.User, userName)

    @defer.inlineCallbacks
    def getOrAddUser(self, userName):
        try:
            ret = yield self.getUser(userName)
        except KeyError:
            self.debug('User %r does not exist, adding', userName)
            u = couch.User(name=userName)
            yield self.db.saveDoc(self.dbName, u._data)
            ret = yield self.getUser(userName)

        defer.returnValue(ret)

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
        total += 1

        self.debug('kept %d of %d track scores', len(result), total)
        self.debug('first track score %r', result[0])

        return result

    def loadTracksFromTrackScores(self, trackScores):
        """
        @returns: a L{defer.Deferred}
                  firing a list of (succeeded, Track/failure)
        @rtype:   a L{defer.Deferred}
                  firing a list of (bool, L{Track}/Failure)
 
        """
        d = manydef.DeferredListSpaced()

        for trackScore in list(trackScores):
            d.addCallable(self.db.map,
                self.dbName, trackScore.subjectId, couch.Track)

        d.start()

        return d

    def resolveTrackSlices(self, track):
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
        d = self.db.map(self.dbName, unicode(file.directory_id), couch.Directory)

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
                    self.dbName, unicode(obj.parent_id), couch.Directory)
            elif getattr(obj, 'volume_id', None):
                d = self.db.map(self.dbName, unicode(obj.volume_id), couch.Volume)

            assert d, 'child %r did not have parent path or volume' % obj

            d.addCallback(cb, parts)

            return d

            d.addCallback(cb, parts)
         
        d.addCallback(cb, [file.name, ])

        return d

class CouchDBModel(base.Model, log.Loggable):

    def __init__(self, daddb):
        self._daddb = daddb

class ArtistSelectorModel(artist.ArtistSelectorModel, CouchDBModel):
    def get(self):
        """
        @returns: a deferred firing a list of L{daddb.ItemTracksByArtist}
                  objects representing only artists and their track count.
        """
        start = time.time()
        self.debug('get')
        v = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'view-tracks-by-artist',
            ItemTracksByArtist)
        try:
            d = v.queryView()
        except Exception, e:
            print 'THOMAS: exception', e
            return defer.fail(e)

        def cb(itemTracks):
            # convert list of ordered itemTracks
            # into a list of ItemTracks with track counts
            artists = {} # artist sortname -> name, id, count

            for item in itemTracks:
                if item.sortname not in artists:
                    artists[item.sortname] = item
                artists[item.sortname].tracks += 1

            ret = artists.values()

            self.debug('get: got %d artists in %.3f seconds',
                len(ret), time.time() - start)
            return ret
        d.addCallback(cb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        return d

# FIXME: convert to inline deferreds
class AlbumSelectorModel(CouchDBModel):

    artistAlbums = None # artist id -> album ids

    def get(self):
        """
        @returns: a deferred firing a list of L{ItemAlbumsByArtist} objects
                  representing only albums and their track count.
        """
        self.debug('get')

        d = defer.Deferred()

        # first, load a mapping of artists to albums
        view = views.View(self._daddb.db, self._daddb.dbName,
            'dad', 'view-albums-by-artist',
            ItemAlbumsByArtist, group=True)
        d.addCallback(lambda _, v: v.queryView(), view)
        
        def cb(result):
            self.artistAlbums = {}

            result = list(result)
            self.debug('Got %d artist/albums combos', len(result))

            for item in result:
                if item.artistId not in self.artistAlbums:
                    self.artistAlbums[item.artistId] = []
                self.artistAlbums[item.artistId].append(item.id)
            return result
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

        self.debug('Getting album ids for artist ids %r', artist_ids)
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
    def get(self, cb=None, *cbArgs, **cbKWArgs):
        """
        @returns: a deferred firing a list of L{daddb.TrackRow} objects.
        """
        d = defer.Deferred()

        self.debug('get')
        last = [time.time(), ]
        start = last[0]


        def loadTracks(_):
            vd = self._daddb.viewDocs('view-tracks-title-artistid', TrackRow)
            def eb(f):
                print 'THOMAS: failure', f
                return f
            vd.addErrback(eb)
            return vd
        d.addCallback(loadTracks)

        def loadTracksCb(tracks):
            # tracks: list of Track
            # import code; code.interact(local=locals())
            trackList = list(tracks)
            self.debug('got %r tracks in %.3f seconds',
                len(trackList), time.time() - last[0])
            last[0] = time.time()

            ret = []
            for trackRow in trackList:
                track = couch.Track()
                d = {
                    'id': trackRow.id,
                    'name': trackRow.name,
                    'artists': trackRow.artists
                }
                track.fromDict(d)
                ret.append(track)

            return ret


        d.addCallback(loadTracksCb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        self.debug('get(): calling back deferred chain')

        d.callback(None)
        return d

class ScorableModel(CouchDBModel):
    """
    I represent a subject in a CouchDB database that can be scored.
    """

    subjectType = 'none'

    def getCategories(self):
        return self._daddb.getCategories()

    @defer.inlineCallbacks
    def getScores(self, userName=None):
        """
        Get a subject's scores and resolve their user and category.

        @rtype: list of user, category, score
        """

        userId = None
        # for now, skip adding actual User docs
        # if userName:
        #     user = yield self._daddb.getOrAddUser(userName)
        #     # FIXME: unicode
        #     user.Id = unicode(user.id)

        # FIXME: the subject controller has .subject, not .track or .artist?
        # subject = getattr(self, self.subjectType)
        # self.debug('Getting scores for %r', subject)
        # scores = yield self._daddb.getScores(subject)
        scores = yield self._daddb.getScores(self.subject)

        scores = list(scores)
        defer.returnValue(scores)

    def score(self, subject, userName, categoryName, score):
        return self._daddb.score(subject, userName, categoryName, score)

class TrackModel(ScorableModel):
    """
    I represent a track in a CouchDB database.

    @ivar track: a track as returned by the database.
    """

    subjectType = 'track'

    track = None

    def get(self, trackId):
        """
        Get a track by id and resolve its artists.

        @returns: a deferred firing a L{couch.Track} object.
        """
        d = self._daddb.db.map(self._daddb.dbName, trackId, couch.Track)
        d.addCallback(lambda track:
            self._daddb.resolveIds(track, 'artist_ids', 'artists',
            couch.Artist))

        d.addCallback(lambda track: setattr(self, 'track', track))
        d.addCallback(lambda _, s: s.track, self)
        return d

class ArtistModel(ScorableModel):
    """
    I represent an artist in a CouchDB database.
    """
    subjectType = 'artist'

    def get(self, artistId):
        """
        Get an artist by id.

        @returns: a deferred firing a L{couch.Artist} object.
        """
        d = self._daddb.db.map(self._daddb.dbName, artistId, couch.Artist)

        d.addCallback(lambda artist: setattr(self, 'artist', artist))
        d.addCallback(lambda _, s: s.artist, self)
        return d

class AlbumModel(ScorableModel):
    """
    I represent an album in a CouchDB database.
    """
    subjectType = 'album'

    def get(self, albumId):
        """
        Get an artist by id.

        @returns: a deferred firing a L{couch.Artist} object.
        """
        d = self._daddb.db.map(self._daddb.dbName, albumId, couch.Album)

        d.addCallback(lambda album: setattr(self, 'album', album))
        d.addCallback(lambda _, s: s.album, self)
        return d
