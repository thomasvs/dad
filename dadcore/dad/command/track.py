# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The track command
"""

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


class Track(logcommand.LogCommand):

    subCommandClasses = [List, ]

    description = 'Interact with tracks.'
