# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Interaction with the database.
"""

import os


from twisted.internet import reactor
from twisted.internet import defer
from twisted.web import error

from dad.extern.task import task
from dadcouch.extern.paisley import client

from dad.common import log
from dad.common import logcommand
from dad.task import md5task

from dadcouch.model import daddb, couch
from dadcouch.selecter import couch as scouch


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
        @type  path: unicode

        @returns:
          - None if it was already in the database.
          - ([existing], [new]) tracks for this path
        """
        self.debug('Adding %s', path)
        if not os.path.exists(path):
            raise PathError(path)

        # look up first
        if not hostname:
            hostname = self._hostname()

        res = yield self.database.getTrackByHostPath(
            hostname, path)
        res = list(res)
        self.debug('Looked up: %r', res)
        if len(res) > 0:
            if not force:
                self.debug('%s already in database', path)
                defer.returnValue(None)
                return

        # doesn't exist, so add it
        self.debug('md5sum %s', path)

        t = md5task.MD5Task(path)
        self._runner.run(t)

        # check if any tracks have a file with this md5sum
        res = yield self.database.getTrackByMD5Sum(t.md5sum)
        res = list(res)

        if res:
            ret = []

            # FIXME: rewrite to use tracks instead of id
            for row in res:
                self.debug('Adding to track with id %r\n' %
                    row.id)
                track = yield self.database.trackAddFragmentFile(row.id,
                    hostname, path,
                    t.md5sum)
                ret.append(track)

            defer.returnValue((ret, []))

            return

        # no tracks with this md5sum, so add it

        track = self.database.new()
        self.database.trackAddFragment(track, host=hostname,
            path=path, md5sum=t.md5sum)

        try:
            stored = yield self.database.save(track)
        except error.Error, e:
            if e.status == 404:
                self.warning('Database or view does not exist.\n')
                yield e
                return

        self.debug('Stored in database as %r\n' %
             stored)

        defer.returnValue(([], [track, ]))
        yield
