# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

import time
import random

from twisted.internet import defer

from zope import interface

from dad import idad
from dad.base import database

from dadcouch.database import mappings, internal
from dadcouch.model import base, artist, track, album


class DADDB(database.Database):
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

        self._internal = internal.InternalDB(db, dbName)

    ## idad.IDatabase interface
    def newTrack(self, name, sort=None, mbid=None):
        return track.CouchTrackModel.new(self, name, sort, mbid)

    @defer.inlineCallbacks
    def getTrack(self, trackId):
        model = track.CouchTrackModel(self)
        model.document = yield self.map(trackId, mappings.Track)
        defer.returnValue(model)

    def newArtist(self, name, sort=None, mbid=None):
        return artist.CouchArtistModel.new(self, name, sort, mbid)

    @defer.inlineCallbacks
    def getOrCreateArtist(self, name, sort=None, mbid=None):
        am = artist.CouchArtistModel.new(self, name, sort, mbid)
        am = yield am.getOrCreate()
        defer.returnValue(am)
        return

        # FIXME: remove this code or fold it into the class method
        # look up by mbid or name
        mid = None
        if mbid:
            mid = u'artist:mbid:' + mbid
        elif name:
            mid = u'artist:name:' + name

        if mid:
            self.debug('Looking up by mid %r', mid)
            # FIXME: convert to class method ?
            model = yield artist.CouchArtistModel.new(self, name, sort, mbid)
            model = yield model.get(mid)
            self.debug('Looked up by mid %r, model %r', mid, model)

        if not model:
            self.debug('Creating new artist for mid %r', mid)
            model = yield artist.CouchArtistModel.new(self, name, sort, mbid)

        defer.returnValue(model)

    def newAlbum(self, name, sort=None, mbid=None):
        return album.CouchAlbumModel.new(self, name, sort, mbid)


    # FIXME: use internal save ?
    @defer.inlineCallbacks
    def save(self, item):
        """
        @type item; L{base.CouchDocModel}
        """
        if isinstance(item, base.CouchDocModel):
            stored = yield self._internal.saveDoc(item.document)
            # FIXME: for now, look it up again to maintain the track illusion
            item.document = yield self._internal.db.map(
                self.dbName, stored['id'],
                item.document.__class__)
            self.debug('saved item doc %r', item.document)
            defer.returnValue(item)
        else:
            raise AttributeError, \
                "Cannot save item of class %r" % item.__class__

    # FIXME: this actually still yields models I think
    def getTracks(self):
        return self._internal.getTracks()

    @defer.inlineCallbacks
    def setScore(self, subject, userName, categoryName, score):
        """
        @type subject: L{base.ScorableModel}
        """
        assert isinstance(subject, base.ScorableModel), \
            "subject %r is not a scorable" % subject
        if not subject.document:
            subject = yield subject.getOrCreate()
        assert subject.document, \
            "subject %r does not have a document" % subject
        doc = yield self._internal.setScore(subject.document,
            userName, categoryName, score)
        subject.document = doc
        defer.returnValue(subject)

    def getScores(self, subject):
        """
        @returns: deferred firing list of L{data.Score}
        """
        assert isinstance(subject, base.ScorableModel), \
            "subject %r is not scorable" % subject
        return self._internal.getScores(subject.document)

    def getCalculatedScores(self, tm):
        """
        @returns: deferred firing list of L{data.Score}
        """
        assert isinstance(tm, track.CouchTrackModel), \
            "track %r is not a track" % track
        return self._internal.getCalculatedScores(tm.document)

    @defer.inlineCallbacks
    def setCalculatedScore(self, subject, userName, categoryName, score):
        """
        @type subject: L{track.TrackModel}
        """
        assert isinstance(subject, track.CouchTrackModel), \
            "subject %r is not a scorable" % subject
        doc = yield self._internal.setCalculatedScore(subject.document,
            userName, categoryName, score)
        subject.document = doc
        defer.returnValue(subject)


    def addCategory(self, name):
        return self._internal.addCategory(name)

    def getCategories(self):
        return self._internal.getCategories()

    @defer.inlineCallbacks
    def getTracksByHostPath(self, host, path):
        """
        Look up tracks by path.
        Can return multiple tracks for a path; for example, multiple
        fragments.


        @type  host: unicode
        @type  path: unicode

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{track.TrackModel}
        """
        gen = yield self._internal.getTracksByHostPath(host, path)

        defer.returnValue(self._wrapTrackDocuments(gen))

    def trackAddFragment(self, track, info, metadata=None, mix=None, number=None):
        return track.addFragment(info, metadata, mix, number)

    @defer.inlineCallbacks
    def getTracksByMD5Sum(self, md5sum):
        """
        Look up tracks by md5sum
        Can return multiple tracks for a path; for example, multiple
        fragments.

        @rtype: a L{defer.Deferred} firing a generator
                returning subclasses of L{dad.model.track.TrackModel}
        """
        gen = yield self._internal.getTracksByMD5Sum(md5sum)

        defer.returnValue(self._wrapTrackDocuments(gen))

    @defer.inlineCallbacks
    def getTracksByMBTrackId(self, mbTrackId):
        """
        Look up tracks by musicbrainz track id.

        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{mappings.Track}
        """
        gen = yield self._internal.getTracksByMBTrackId(mbTrackId)

        defer.returnValue(self._wrapTrackDocuments(gen))

    def _wrapTrackDocuments(self, gen):
        for doc in gen or []:
            model = self.newTrack(doc.name)
            model.document = doc
            yield model

    def trackAddFragmentFileByMD5Sum(self, track, info, metadata=None, mix=None, number=None):
        """
        Add the given file to each fragment with a file with the same md5sum.
        """
        return self._internal.trackAddFragmentFileByMD5Sum(
            track.document, info, metadata, mix, number)

    def trackAddFragmentFileByMBTrackId(self, track, info, metadata, mix=None, number=None):
        return self._internal.trackAddFragmentFileByMBTrackId(
            track.document, info, metadata, mix, number)

    def trackAddFragmentChromaPrint(self, track, info, chromaprint):
        """
        Add the given chromaprint to the given track for the given info.
        """
        return self._internal.trackAddFragmentChromaPrint(
            track.document, info, chromaprint)


    @defer.inlineCallbacks
    def getPlaylist(self, hostName, userName, categoryName, above, below, limit=None,
        randomize=False):
        """
        @type  limit:        int or None
        @type  randomize:       bool

        @returns: deferred firing a generator of tracks and additional info
        @rtype: L{defer.Deferred} firing
                list of Track, Slice, path, score, userId
        """
        start = time.time()

        self.debug('Getting tracks for host %r and category %r and user %r',
            hostName, categoryName, userName)

        startkey = [userName, categoryName, above]
        endkey = [userName, categoryName, below]

        gen = yield self._internal.viewDocs('view-scores-host',
            mappings.Track,
            startkey=startkey, endkey=endkey, include_docs=True)

        # FIXME: filter on host ?

        # FIXME: for randomness, we currently go from generator to
        # full list and back
        if randomize:
            tracks = [t for t in gen]
            random.shuffle(tracks)
            gen = self._randomizer((t for t in tracks),
                userName, categoryName, above, below)

        self.debug('created playlist generator in %.3f seconds',
            time.time() - start)
        defer.returnValue(gen)

    def _randomizer(self, gen, userName, categoryName, above, below):
        """
        Given a generator of tracks, returns a generator that yields
        results randomly.
        """

        for t in gen:
            # FIXME: should also apply if non-random
            score = t.getCalculatedScore(userName, categoryName)
            if not score:
                print 'THOMAS: ERROR: no score for', t
                continue
            prob = float(score.score - above) / float(below - above)
            r = random.random()

            skipping = True
            if r < prob:
                skipping = False

            self.debug('Track %r with probability %.3f and random %.3f, %s',
                t.getName(), prob, r, skipping and 'skipping' or 'yielding')
            if not skipping:
                yield t


    ### own instance methods
    def map(self, docId, objectFactory):
        return self.db.map(self.dbName, docId, objectFactory)

    def modelFactory(self, modelClass):
        return lambda: modelClass(daddb=self)
