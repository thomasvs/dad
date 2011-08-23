# -*- Mode: Python; test_case_name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import sys
import time
import pickle

from twisted.internet import defer

from zope import interface

from dad import idad
from dad.base import base, data
from dad.common import log

class File(object):
    host = None
    path = None

class Fragment(object):
    def __init__(self):
        self.files = []

class Track(object):
    """
    @ivar id: id of the track
    @ivar scores: list of L{data.Score}
    """

    def __init__(self, id):
        self.id = id
        self.scores = []
        self.fragments = []


class MemoryDB(log.Loggable):
    """
    """

    interface.implements(idad.IDatabase)

    logCategory = 'memorydb'

    def __init__(self, path=None):
        self._tracks = {}
        self._categories = {}

        self._hostPath = {} # dict of host -> (dict of path -> track)
        self._id = 0

        self._path = path
        if self._path:
            try:
                self.__dict__ = pickle.load(open(self._path))
            except EOFError:
                # probably empty
                pass

    ### idad.IDatabase interface
    def new(self):
        self._id += 1
        return Track(self._id)

    def save(self, track):
        self._tracks[track.id] = track

        for score in track.scores:
            if not score.category in self._categories:
                self._categories[score.category] = True

        for fragment in track.fragments:
            for file in fragment.files:
                host = file.host
                path = file.path

                if not host in self._hostPath.keys():
                    self._hostPath[host] = {}
                if not path in self._hostPath[host].keys():
                    self._hostPath[host][path] = []
                self._hostPath[host][path].append(track)

        if self._path:
            handle = open(self._path, 'w')
            pickle.dump(self.__dict__, handle, 2)
            
        return defer.succeed(track)

    def getCategories(self):
        return defer.succeed(self._categories.keys())

    def getScores(self, subject):
        """
        @returns: deferred firing list of L{data.Score}
        """
        scores = self._tracks[subject.id].scores
        self.debug('%d scores for %r', len(scores), subject.id)
        return defer.succeed(scores)

    @defer.inlineCallbacks
    def getTrackByHostPath(self, host, path):
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
            return defer.succeed(None)

        if not path in self._hostPath[host].keys():
            self.debug('path %r on host %r not in database', path, host)
            return defer.succeed(None)

        return defer.succeed(self._hostPath[host][path])

    # TOPORT
    def trackAddFragment(self, track, info, metadata=None, mix=None, number=None):
        return track.addFragment(info, metadata, mix, number)

    @defer.inlineCallbacks
    def getTrackByMD5Sum(self, md5sum):
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
    def getTrackByMBTrackId(self, mbTrackId):
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
                    found = True
                    break
            if found:
                break

        stored = yield self.saveDoc(track)

        track = yield self.db.map(self.dbName, stored['id'], couch.Track)
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
        """
        Score the given subject.
        """
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
            s = data.Score()
            s.subject = subject
            s.user = userName
            s.category = categoryName
            s.score = score
            subject.scores.append(s)
            print subject.scores
            ret = yield self.save(subject)

        defer.returnValue(ret)
