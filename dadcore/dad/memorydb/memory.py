# -*- Mode: Python; test-case-name: dad.test.test_memorydb_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import pickle
import optparse

from twisted.internet import defer

from zope import interface

from dad import idad
from dad.base import data, database
from dad.memorydb.model import track, artist

_DEFAULT_PATH = 'dad.pickle'

memorydb_option_list = [
        optparse.Option('-p', '--path',
            action="store", dest="path",
            help="database pickle path (defaults to %default)",
            default=_DEFAULT_PATH),
]


class MemoryDB(database.Database):
    """
    I am a database that stores all data in memory.
    I can be saved to a pickle.
    """

    interface.implements(idad.IDatabase)

    logCategory = 'memorydb'

    def __init__(self, path=None):
        self._tracks = {} # id -> MemoryTrackModel
        self._artists = {} # dict of artist name -> MemoryArtistModel
        self._categories = {}
        self._mbTrackIds = {} # mb track id -> list of MemoryTrackModel

        self._hostPath = {} # dict of host -> (dict of path -> MemoryTrackModel
        self._md5sums = {} # dict of md5sum -> MemoryTrackModel

        self._calculatedScores = {} # dict of MemoryTrackModel -> list of Score

        self._id = 0

        self._path = path
        if self._path:
            try:
                self.__dict__ = pickle.load(open(self._path))
            except (EOFError, IOError):
                # probably empty or nonexistent
                pass
            self.debug('Loaded pickle')
            self.debug('%d tracks', len(self._tracks))
            self.debug('%d artists', len(self._artists))

        self.registerFactory('track', track.MemoryTrackModel)
        self.registerFactory('artist', artist.MemoryArtistModel)
        # self.registerFactory('album', album.MemoryAlbumModel)

    # private methods
    def _save(self):
        # save to disk
        if self._path:
            self.debug('persisting to disk')
            handle = open(self._path, 'w')
            pickle.dump(self.__dict__, handle, 2)
            handle.close()

    ### idad.IDatabase interface
    @defer.inlineCallbacks
    def getOrCreateArtist(self, name, sort=None, mbid=None):
        # look up by mbid or name
        mid = None
        if mbid:
            mid = u'artist:mbid:' + mbid
        elif name:
            mid = u'artist:name:' + name

        if mid:
            self.debug('Looking up by mid %r', mid)
            if name in self._artists:
                model = self._artists[name]
            self.debug('Looked up by mid %r, model %r', mid, model)

        if not model:
            self.debug('Creating new artist for mid %r', mid)
            model = yield self.newArtist(name, sort, mbid)

        defer.returnValue(model)


    # FIXME: make generic
    def save(self, subject):
        if isinstance(subject, track.MemoryTrackModel):
            return self._saveTrack(subject)
        elif isinstance(subject, artist.MemoryArtistModel):
            return self.saveArtist(subject)
        raise TypeError('Cannot save subject %r' % subject)

    def _saveTrack(self, track):
        if track.id is None:
            self._id += 1
            track.id = self._id
        self._tracks[track.id] = track

        for fragment in track.fragments:
            for file in fragment.files:
                host = file.info.host
                path = file.info.path

                if not host in self._hostPath.keys():
                    self._hostPath[host] = {}
                if not path in self._hostPath[host].keys():
                    self._hostPath[host][path] = []
                self._hostPath[host][path].append(track)

                if not file.info.md5sum in self._md5sums.keys():
                    self._md5sums[file.info.md5sum] = []
                self._md5sums[file.info.md5sum].append(track)

                if file.metadata and file.metadata.mbTrackId:
                    mb = file.metadata.mbTrackId
                    if not mb in self._mbTrackIds:
                        self._mbTrackIds[mb] = []
                    self._mbTrackIds[mb].append(track)


        # FIXME: work with id ?
        for name in track.getArtistNames():
            if not name in self._artists:
                am = artist.MemoryArtistModel(self)
                am.name = name
                am.tracks = [track, ]
                self._artists[name] = am
            else:
                self._artists[name].tracks.append(track)

        self._save()

        return defer.succeed(track)


    def getTracks(self):
        return self._tracks.values()

    def getCategories(self):
        return defer.succeed(self._categories.keys())

    def getScores(self, subject):
        """
        @returns: deferred firing list of L{data.Score}
        """
        if isinstance(subject, track.MemoryTrackModel):
            scores = self._tracks[subject.getId()].scores
            self.debug('%d scores for %r', len(scores), subject.id)
            return defer.succeed(scores)
        elif isinstance(subject, artist.MemoryArtistModel):
            scores = self._artists[subject.getName()].scores
            self.debug('%d scores for %r', len(scores), subject.id)
            return defer.succeed(scores)
        else:
            raise AttributeError('No way to get scores for class %r' %
                subject.__class__)

    def getCalculatedScores(self, subject):
        """
        @returns: deferred firing list of L{data.Score}
        """
        scores = self._calculatedScores.get(subject, [])
        return defer.succeed(scores)


    @defer.inlineCallbacks
    def setCalculatedScore(self, subject, userName, categoryName, score):
        found = False

        for i, s in enumerate(self._calculatedScores.get(subject, [])):
            if s.user == userName and s.category == categoryName:
                self.debug('Updating score for %r in %r from %r to %r',
                    userName, categoryName, s.score, score)
                self._calculatedScores[subject][i].score = score
                found = True

        if not found:
            self.debug('Setting score for %r in %r to %r',
                userName, categoryName, score)
            if not self._calculatedScores.has_key(subject):
                self._calculatedScores[subject] = []
            s = data.Score()
            s.subject = subject
            s.user = userName
            s.category = categoryName
            s.score = score
            self._calculatedScores[subject].append(s)
        ret = yield self._save()

        defer.returnValue(subject)


    def getTracksByHostPath(self, host, path):
        """
        @type  host: unicode
        @type  path: unicode

        @rtype: L{defer.Deferred} firing list of L{track.MemoryTrackModel}
        """
        assert type(host) is unicode, \
            'host is type %r, not unicode' % type(host)
        assert type(path) is unicode, \
            'host is type %r, not unicode' % type(path)

        self.debug('get track for host %r and path %r', host, path)

        if not host in self._hostPath.keys():
            self.debug('host %r not in database', host)
            return defer.succeed(xrange(0))

        if not path in self._hostPath[host].keys():
            self.debug('path %r on host %r not in database', path, host)
            return defer.succeed(xrange(0))

        # FIXME: does returning a list count as a generator ?
        return defer.succeed(t for t in self._hostPath[host][path])

    def getTracksByMD5Sum(self, md5sum):
        """
        Look up tracks by md5sum
        Can return multiple tracks for a path; for example, multiple
        fragments.

        @rtype: L{defer.Deferred} firing list of L{track.MemoryTrackModel}
        """
        return defer.succeed(self._md5sums.get(md5sum, []))

    def getTracksByMBTrackId(self, mbTrackId):
        """
        Look up tracks by musicbrainz track id.

        Can return multiple tracks for a path; for example, multiple
        fragments.

        ### FIXME:
        @rtype: L{defer.Deferred} firing list of L{couch.Track}
        """
        self.debug('get track for mb track id %r', mbTrackId)
        if mbTrackId in self._mbTrackIds:
            return defer.succeed(self._mbTrackIds[mbTrackId])

        return defer.succeed([])

    @defer.inlineCallbacks
    def trackAddFragmentFileByMD5Sum(self, track, info, metadata=None, mix=None, number=None):
        """
        Add the given file to each fragment with a file with the same md5sum.
        """
        # FIXME: possibly raise if we don't find it ?
        found = False

        for fragment in track.fragments:
            for f in fragment.files:
                if f.info.md5sum == info.md5sum:
                    self.debug('Appending to fragment %r', fragment)
                    track.filesAppend(fragment.files, info, metadata, number)
                    found = True
                    break
            if found:
                break

        if not found:
            self.debug('MD5 sum %r not found on track', info.md5sum)
        else:
            track = yield self.save(track)

        defer.returnValue(track)

    @defer.inlineCallbacks
    def trackAddFragmentFileByMBTrackId(self, track, info, metadata, mix=None, number=None):
        self.debug('get track for track id %r', track.id)

        # FIXME: possibly raise if we don't find it ?
        found = False

        if len(track.fragments) > 1:
            self.warning('Not yet implemented finding the right fragment to add by mbid')

        for fragment in track.fragments:
            for f in fragment.files:
                if f.metadata and f.metadata.mbTrackId == metadata.mbTrackId:
                    self.debug('Appending to fragment %r', fragment)
                    track.filesAppend(fragment.files, info, metadata, number)
                    found = True
                    break
            if found:
                break

        stored = yield self.save(track)

        defer.returnValue(track)

    @defer.inlineCallbacks
    def setScore(self, subject, userName, categoryName, score):
        self.debug('asked to score subject %r '
            'for user %r and category %r to score %r',
            subject, userName, categoryName, score)

        found = False
        ret = None

        if not categoryName in self._categories:
            self.debug('Adding category %r', categoryName)
            self._categories[categoryName] = True

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
            s = data.Score()
            s.subject = subject
            s.user = userName
            s.category = categoryName
            s.score = score
            subject.scores.append(s)
            ret = yield self.save(subject)

        self._save()

        defer.returnValue(ret)

    def getDuplicateTracks(self):
        ret = []

        for mbtrackid, tracks in self._mbTrackIds.items():
            if len(tracks) > 1:
                ret.append((mbtrackid, tracks))

        return ret

    ### implementation methods
    def saveArtist(self, artist):
        """
        @type  artist: L{artist.ArtistModel}
        """
        if artist.id is None:
            self._id += 1
            artist.id = self._id
        # FIXME: use interface, getName ?
        self._artists[artist.name] = artist
        self._save()
        return artist

    # TOPORT
    def trackAddFragment(self, track, info, metadata=None, mix=None, number=None):
        return track.addFragment(info, metadata, mix, number)
