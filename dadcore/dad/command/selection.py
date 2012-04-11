# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Commands related to selections.
"""

from twisted.internet import defer

from dad.common import logcommand
from dad.command import tcommand
 

class List(tcommand.TwistedCommand):
    summary = """List selections in the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        gen = yield self.parentCommand.parentCommand.database.getSelections()
        i = 0
        for name in gen:
            i += 1
            self.stdout.write('%s\n' % name)
        self.stdout.write('%d selections\n' % i)
 
class Show(tcommand.TwistedCommand):
    summary = """Show a selection in the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        if not args:
            self.stderr.write('Please give selections to show.\n')
            defer.returnValue(3)
            return


        for name in args:
            selection = yield self.parentCommand.parentCommand.database.getSelection(name)
            print selection
            tracks = yield selection.get()
            for track in tracks:
                print track

# FIXME: move to database, not couchdb
class Selection(logcommand.LogCommand):

    summary = """Interact with selections."""

    subCommandClasses = [List, Show]
