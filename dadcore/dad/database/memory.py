# -*- Mode: Python; test_case_name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import time
import pickle
import optparse

from twisted.internet import defer

from zope import interface

from dad import idad
from dad.base import base, data
from dad.common import log
from dad.model import track, artist

_DEFAULT_PATH = 'dad.pickle'

memorydb_option_list = [
        optparse.Option('-p', '--path',
            action="store", dest="path",
            help="database pickle path (defaults to %default)",
            default=_DEFAULT_PATH),
]


class MemoryModel(base.Model):
    def __init__(self, memorydb):
        self._db = memorydb

class MemoryArtistModel(artist.ArtistModel):
    """
    @ivar id:     id of the artist
    @ivar name:   name of the artist
    @type tracks: int
    """
    id = None
    name = None

    tracks = 0

    def getId(self):
        if self.id:
            return self.id

        return self.name

    def getName(self):
        return self.name

    def getSortName(self):
        return self.name

    def getTrackCount(self):
        return self.tracks


class MemoryTrackModel(track.TrackModel):
    """
    @ivar id:     id of the track
    @ivar scores: list of L{data.Score}
    """

    def __init__(self, id):
        self.id = id
        self.scores = []
        self.fragments = []
        self.name = None

    # base class implementations

    def addFragment(self, info, metadata=None, mix=None, number=None):
        fragment = track.FragmentModel()
        file = track.FileModel()
        file.info = info
        file.metadata = metadata

        fragment.files.append(file)
        self.fragments.append(fragment)
    
    def getName(self):
        if self.name:
            return self.name

        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata:
                    return file.metadata.title

    def getArtists(self):
        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata:
                    return [file.metadata.artist, ]

        return []

    def getFragments(self):
        return self.fragments
        
    # specific methods
    # FIXME: handle this better in both models
    def filesAppend(self, files, info, metadata=None, number=None):
        file = track.FileModel()
        file.info = info
        file.metadata = metadata
        file.number = number

        files.append(file)

class MemoryArtistSelectorModel(artist.ArtistSelectorModel, MemoryModel):
    def get(self):
        return defer.succeed(self._db._artists.values())
    

class MemoryDB(log.Loggable):
    """
    """

    interface.implements(idad.IDatabase)

    logCategory = 'memorydb'

    def __init__(self, path=None):
        self._tracks = {} # id -> track
        self._artists = {} # dict of artist name -> (MemoryArtistModel, count)
        self._categories = {}
        self._mbTrackIds = {} # mb track id -> track

        self._hostPath = {} # dict of host -> (dict of path -> track)
        self._md5sums = {} # dict of md5sum -> track

        self._id = 0

        self._path = path
        if self._path:
            try:
                self.__dict__ = pickle.load(open(self._path))
            except (EOFError, IOError):
                # probably empty or nonexistent
                pass

    # private methods
    def _save(self):
        # save to disk
        if self._path:
            self.debug('persisting to disk')
            handle = open(self._path, 'w')
            pickle.dump(self.__dict__, handle, 2)
            handle.close()

 
    ### idad.IDatabase interface
    def new(self):
        self._id += 1
        return MemoryTrackModel(self._id)

    def save(self, track):
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


        for artist in track.getArtists():
            if not artist in self._artists:
                am = MemoryArtistModel()
                am.name = artist
                am.tracks = 1
                self._artists[artist] = am
            else:
                self._artists[artist].tracks += 1

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
        scores = self._tracks[subject.id].scores
        self.debug('%d scores for %r', len(scores), subject.id)
        return defer.succeed(scores)

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

        @rtype: L{defer.Deferred} firing list of L{MemoryTrackModel}
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
    def score(self, subject, userName, categoryName, score):
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
    # TOPORT
    def trackAddFragment(self, track, info, metadata=None, mix=None, number=None):
        return track.addFragment(info, metadata, mix, number)


