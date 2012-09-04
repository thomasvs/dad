# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Commands related to categories.
"""

from twisted.internet import defer

from dad.common import logcommand
from dad.command import tcommand


class Add(tcommand.TwistedCommand):
    """
    @type hostname: unicode
    """

    description = """Add a category to the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        if not args:
            self.stderr.write('Please give a category name to add.\n')
            defer.returnValue(3)
            return

        category = args[0]

        ret = yield self.parentCommand.parentCommand.database.getCategories()
        ret = list(ret)
        if category in ret:
            self.stderr.write('Category %s already exists.\n', category)
            defer.returnValue(3)
            return

        ret = yield self.parentCommand.parentCommand.database.addCategory(
            category)

class List(tcommand.TwistedCommand):
    description = """List categories in the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        ret = yield self.parentCommand.parentCommand.database.getCategories()
        ret = list(ret)
        for cat in ret:
            self.stdout.write('%s\n' % cat)
        self.stdout.write('%d categories\n' % len(ret))


class Category(logcommand.LogCommand):

    subCommandClasses = [Add, List, ]

    description = 'Handle categories'

