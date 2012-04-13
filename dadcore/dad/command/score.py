# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Commands related to scores.
"""

import getpass

from twisted.internet import defer

from dad.extern.command import command

from dad.common import logcommand
from dad.command import tcommand, common
from dad.logic import database


class PathCommand(tcommand.TwistedCommand):

    def addOptions(self):
        self.parser.add_option('-H', '--hostname',
                          action="store", dest="hostname",
                          default=common.hostname(),
                          help="override hostname (%default)")

    def handleOptions(self, options):
        self.hostname = options.hostname.decode('utf-8')


    @defer.inlineCallbacks
    def doLater(self, args):
        if not args:
            self.stderr.write('Please give path to get scores for.\n')
            defer.returnValue(3)
            return

        self.interactor = database.DatabaseInteractor(
            self.parentCommand.parentCommand.database,
            self.parentCommand.parentCommand.runner)

        paths = common.expandPaths(args, self.stderr)

        for path in paths:
            yield self.doPath(path)

    ### subclass methods

    def doPath(self, path):
        raise NotImplementedError


class Get(PathCommand):
    """
    @type hostname: unicode
    """

    description = """Get scores for the given track."""
    
    @defer.inlineCallbacks
    def doPath(self, path):
        gen = yield self.interactor.lookup(path, hostname=self.hostname)
        for model in gen:
            scores = yield model.getCalculatedScores()
            self.stdout.write('%r:\n' % model)
            scores = list(scores)
            for score in scores:
                self.stdout.write('%r\n' % score)
            if not scores:
                self.stdout.write('No scores\n')


_DEFAULT_CATEGORY = u'Good'
class Set(PathCommand):
    description = """Set score for the given track."""

    def addOptions(self):
        PathCommand.addOptions(self)

        self.parser.add_option('-u', '--user',
            action="store", dest="user",
            help="user (defaults to current user %default)",
            default=getpass.getuser())
        self.parser.add_option('-c', '--category',
            action="store", dest="category",
            help="category to make playlist for (defaults to %default)",
            default=_DEFAULT_CATEGORY)
        self.parser.add_option('-s', '--score',
            action="store", dest="score", type="float",
            help="score between 0.0 and 1.0")
 
    def handleOptions(self, options):
        PathCommand.handleOptions(self, options)

        if not options.score:
            raise command.CommandError('Please specify a score.')

    @defer.inlineCallbacks
    def doPath(self, path):
        gen = yield self.interactor.lookup(path, hostname=self.hostname)
        for model in gen:
            ret = yield model.score(self.options.user, self.options.category,
                self.options.score)
            print ret
 

class Score(logcommand.LogCommand):

    subCommandClasses = [Get, Set, ]

    description = 'Handle scores'

