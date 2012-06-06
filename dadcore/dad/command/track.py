# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The track command
"""

import os

from twisted.internet import defer

from dad.common import logcommand
from dad.command import tcommand

class List(tcommand.TwistedCommand):

    description = """List all tracks in the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        db = self.parentCommand.parentCommand.database
        res = yield db.getTracks()
        for track in res:
            self.stdout.write('%s - %s\n' % (
                " & ".join(track.getArtistNames()), track.getName()))


class Duplicates(tcommand.TwistedCommand):

    description = """List all duplicate tracks in the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        db = self.parentCommand.parentCommand.database
        res = yield db.getDuplicateTracks()
        count = 0

        for mbtrackid, tracks in res:
            count += 1
            self.stdout.write('mbtrackid: %s\n' % mbtrackid)
            for track in tracks:
                self.stdout.write('  %s - %s\n' % (
                    " & ".join(track.getArtistNames()), track.getName()))

        self.stdout.write('%d duplicates\n' % count)

class Missing(tcommand.TwistedCommand):

    description = """List all missing files for tracks in the database."""

    def _hostname(self):
        import socket
        return unicode(socket.gethostname())

    @defer.inlineCallbacks
    def doLater(self, args):
        db = self.parentCommand.parentCommand.database
        res = yield db.getTracksByHostPath(self._hostname())

        count = 0

        for track in res:
            for fragment in track.getFragments():
                for f in fragment.files:
                    if f.info.host != self._hostname():
                        continue

                    if not os.path.exists(f.info.path):
                        count += 1
                        self.stdout.write('missing path: %s\n' %
                            f.info.path.encode('utf-8'))
                        self.stdout.write('  %s - %s\n' % (
                            " & ".join(track.getArtistNames()),
                            track.getName()))

        self.stdout.write('%d missing files\n' % count)


class Track(logcommand.LogCommand):

    subCommandClasses = [Duplicates, List, Missing]

    description = 'Interact with tracks.'
