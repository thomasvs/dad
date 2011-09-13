# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Interaction with the database.
"""

import os

from twisted import plugin

from twisted.internet import defer

from dad.extern.task import task


from dad import idad
from dad.common import log
from dad.common import logcommand
from dad.task import md5task

class PathError(Exception):
    pass

class DatabaseInteractor(logcommand.LogCommand):
    """
    Interact with a database.
    """

    def __init__(self, database, runner=None):
        self.database = database
        if not runner:
            runner = task.SyncRunner()
        self._runner = runner

    def _hostname(self):
        import socket
        return unicode(socket.gethostname())


    @defer.inlineCallbacks
    def add(self, path, hostname=None, force=False):
        """
        @type  path:     C{unicode}
        @type  hostname: C{unicode}
        @type  force:    C{bool}

        @returns:
          - None if it was already in the database.
          - ([existing], [new]) tracks for this path
        """
        ret = ([], [])

        self.debug('Adding %s', path)
        if not os.path.exists(path):
            raise PathError(path)

        # look up first
        if not hostname:
            hostname = self._hostname()

        res = yield self.database.getTracksByHostPath(
            hostname, path)
        if not res:
            res = []

        res = list(res)
        self.debug('Looked up: %r', res)
        if len(res) > 0:
            if not force:
                self.debug('%s already in database: %r', path, res[0])
                defer.returnValue(ret)
                return

        # doesn't exist, so add it

        # get metadata
        # FIXME: choose ?
        from dad import plugins
        getter = None
        for getter in plugin.getPlugins(idad.IMetadataGetter, plugins):
            continue

        try:
            metadata = getter.getMetadata(path, runner=self._runner)
        except task.TaskException, e:
            print 'ERROR:', log.getExceptionMessage(e)
            print 'skipping', path.encode('utf-8')
            return


        self.debug('Got metadata: %r', metadata)

        # get fileinfo
        t = md5task.MD5Task(path)
        self._runner.run(t)

        info = FileInfo(hostname, path, md5sum=t.md5sum)

        stat = os.stat(path)
        info.size = stat.st_size
        info.inode = stat.st_ino
        info.device = stat.st_dev
        info.mtime = stat.st_mtime

        self.debug('Got fileinfo: %r', info)
        
        leveller = None
        for leveller in plugin.getPlugins(idad.ILeveller, plugins):
            continue

        if not leveller:
            self.error('Please make sure you have a leveller plugin installed.')
        trackMixes = leveller.getTrackMixes(path, runner=self._runner)
        self.debug('Got track mixes: %r', trackMixes)

        self.debug('File has %d fragments', len(trackMixes))

        for i, mix in enumerate(trackMixes):

            # check if any tracks have a file with this md5sum
            res = yield self.database.getTracksByMD5Sum(info.md5sum)
            res = list(res)

            if res:
                self.debug('Got tracks by md5sum: %r', res)
                retVal = []

                # FIXME: rewrite to use tracks instead of id
                for track in res:
                    self.debug('Adding to track with id %r\n' %
                        track)
                    added = yield self.database.trackAddFragmentFileByMD5Sum(
                        track, info, metadata=metadata, mix=mix, number=i + 1)
                    retVal.append(added)

                ret[0].extend(retVal)

                continue

            # check if any tracks have a file with this musicbrainz id
            if metadata and metadata.mbTrackId:
                res = yield self.database.getTracksByMBTrackId(metadata.mbTrackId)
                res = list(res)

                if res:
                    self.debug('found %d tracks with same mbid', len(res))
                    retVal = []

                    for track in res:
                        self.debug('Adding to track %r\n' % track)
                        added = yield self.database.trackAddFragmentFileByMBTrackId(
                            track, info, metadata=metadata, mix=mix, number=i + 1)
                        retVal.append(added)

                    ret[0].extend(retVal)
                    continue



            # no tracks with this md5sum, so add it

            track = self.database.new()
            self.debug('Adding new track %r, number %r', track, i + 1)
            self.database.trackAddFragment(track, info, metadata=metadata, mix=mix, number=i + 1)

            # imports reactor
            from twisted.web import error
            try:
                stored = yield self.database.save(track)
            except error.Error, e:
                if e.status == 404:
                    self.warning('Database or view does not exist.\n')
                    yield e
                    continue

            self.debug('Stored in database as %r\n' % stored)

            ret[1].append(track)
            yield

        defer.returnValue(ret)

    def score(self, model, userName, categoryName, score):
        """
        Score the given model.
        Recalculates track scores if needed.
        """
        # FIXME: remove method
        return self.database.score(model, userName, categoryName, score)
    
    def recalculateTrackScore(self, tm):
        """
        Recalculate the aggregate track score of a track, taking into account
        artist and album scores.

        @type  tm: L{dad.model.track.TrackModel}
        """
        return self.database.recalculateTrackScore(tm)

class FileInfo:
    """
    A class for collecting information about a file.
    """
    host = None
    path = None
    md5sum = None
    mtime = None  # epoch seconds
    device = None # int; result st_dev from stat
    inode = None  # int; result st_ino from stat
    size = None   # int; result st_size from stat

    def __init__(self, host, path, md5sum=None):
        self.host = host
        self.path = path
        self.md5sum = md5sum

    def __repr__(self):
        return "<FileInfo for %s on %s (%d bytes)>" % (
            self.path or None, self.host or None, self.size or -1)

class TrackMetadata:
    """
    A class for collecting a file's metadata and stream information.
    """

    artist = None
    title = None
    album = None
    trackNumber = None
    year = None
    month = None
    day = None

    # stream information
    audioCodec = None
    sampleRate = None
    channels = None
    length = None


    # musicbrainz
    mbTrackId = None
    mbArtistId = None
    mbAlbumId = None
    mbAlbumArtistId = None

    def __repr__(self):
        return "<TrackMetadata for %s - %s>" % (
            self.artist or None, self.title or None)
