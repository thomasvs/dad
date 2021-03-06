# -*- Mode: Python; test-case-name: dadcouch.test.test_database_couch -*-
# vi:si:et:sw=4:sts=4:ts=4

import optparse
import time
import random

from twisted.internet import defer

from zope import interface

from dad import idad
from dad.base import database

from dadcouch.database import mappings, internal
from dadcouch.model import base, artist, track, album

_DEFAULT_HOST = 'localhost'
_DEFAULT_PORT = 5984
_DEFAULT_DB = 'dad'

couchdb_option_list = [
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
]

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
        self.registerFactory('track', track.CouchTrackModel)
        self.registerFactory('artist', artist.CouchArtistModel)
        self.registerFactory('album', album.CouchAlbumModel)

    ## idad.IDatabase interface
    @defer.inlineCallbacks
    def getTrack(self, trackId):
        model = track.CouchTrackModel(self)
        model.document = yield self.map(trackId, mappings.Track)
        defer.returnValue(model)

    @defer.inlineCallbacks
    def getOrCreateArtist(self, name, sort=None, mbid=None):
        am = artist.CouchArtistModel.new(self, name, sort, mbid)
        am = yield am.getOrCreate()
        defer.returnValue(am)
        return


    # FIXME: use internal save ?
    @defer.inlineCallbacks
    def save(self, item):
        """
        @type item: L{base.CouchBackedModel}
        """
        if isinstance(item, base.CouchBackedModel):
            stored = yield self._internal.saveDoc(item.document)
            # FIXME: for now, look it up again to maintain the track illusion
            item.document = yield self._internal.db.map(
                self.dbName, stored['id'],
                item.document.__class__)
            self.debug('saved doc %r for item %r', item.document, item)
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
        @type subject: L{base.CouchScorableModel}
        """
        assert isinstance(subject, base.CouchScorableModel), \
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
        assert isinstance(subject, base.CouchScorableModel), \
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
    def getTracksByHostPath(self, host, path=None):
        """
        Look up tracks by path.
        Can return multiple tracks for a path; for example, multiple
        fragments.


        @type  host: unicode
        @type  path: unicode or None

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
            model = self.new('track', doc.name)
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

        The chromaprint may contain only chromaprint data
        (chromaprint/duration), or chromaprint lookup data.

        @type  track:       L{dad.model.track.TrackModel}
        @type  chromaprint: L{dad.model.track.ChromaPrintModel}
        """
        return self._internal.trackAddFragmentChromaPrint(
            track.document, info, chromaprint)

    def trackGetFragmentChromaPrint(self, track, info):
        """
        Get the stored chromaprint to the given track for the given info.

        The chromaprint may contain only chromaprint data
        (chromaprint/duration), or chromaprint lookup data.

        @type  track: L{dad.model.track.TrackModel}

        @rtype: L{dad.model.track.ChromaPrintModel}
        """
        return self._internal.trackGetFragmentChromaPrint(
            track.document, info)


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
            # FIXME: this gives probability 0 to tracks at above
            prob = float(score.score - above) / float(below - above)
            prob = float(abs(score.score - 0.5) / float(1.0 - 0.5))
            r = random.random()

            skipping = True
            if r < prob:
                skipping = False

            self.debug('Track %r with score %r, '
                'probability %.3f and random %.3f, %s',
                t.getName(), score.score, prob, r,
                skipping and 'skipping' or 'yielding')
            if not skipping:
                yield t

    def getUrl(self, model):
        return self.db.url_template % ('/_utils/document.html?%s/%s' % (
            self.dbName, model.document.id))

    @defer.inlineCallbacks
    def getDuplicateTracks(self):
        ret = []

        gen = yield self._internal.viewDocs('view-mbtrackid',
            mappings.ViewRow, group_level=1)

        duplicates = [row.key for row in gen if row.value > 1]

        for mbtrackid in duplicates:
            gen = yield self.getTracksByMBTrackId(mbtrackid)
            ret.append((mbtrackid, list(gen)))

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def getSelections(self):
        gen = yield self._internal.viewDocs('view-selections',
            mappings.SelectionRow)

        defer.returnValue((s.name for s in gen))


    @defer.inlineCallbacks
    def getSelection(self, name):
        """
        @rtype: L{dad.model.selection.SelectionModel}
        """
        gen = yield self._internal.viewDocs('view-selections',
            mappings.Selection, key=name, include_docs=True)

        from dadcouch.model import selection
        m = selection.CouchSelectionModel(self)

        docs = list(gen)
        if not docs:
            raise KeyError('No selection %s found' % name)

        m.document = docs[0]

        defer.returnValue(m)

    ### own instance methods
    def map(self, docId, objectFactory):
        return self.db.map(self.dbName, docId, objectFactory)

    def modelFactory(self, modelClass):
        return lambda: modelClass(database=self)
