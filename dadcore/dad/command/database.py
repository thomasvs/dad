# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The database command
"""

import os
import optparse

from twisted import plugin

from twisted.internet import defer

from dad import idad

from dad.common import log
from dad.common import logcommand
from dad.command import tcommand, category, score, selection, common, track
from dad.logic import database

from dad.extern.task import task

class Add(tcommand.TwistedCommand):
    """
    @type hostname: unicode
    """

    description = """Add audio files to the database."""
    hostname = None

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
            self.stderr.write('Please give paths to add.\n')
            defer.returnValue(3)
            return

        interactor = database.DatabaseInteractor(
            self.parentCommand.database,
            self.parentCommand.runner)

        # FIXME: database-specific, should be replaced by more generic things
        # FIXME: imports reactor
        from twisted.web import error

        paths = common.expandPaths(args, self.stderr)

        failed = []
        for path in paths:
            path = os.path.abspath(path)
            self.stdout.write('%s\n' % path.encode('utf-8'))

            d = interactor.add(path, hostname=self.hostname)
            d.addErrback(log.warningFailure)
            try:
                res = yield d
            except error.Error, e:
                if e.status == 404:
                    self.stderr.write('Database or view does not exist.\n')
                    self.reactor.stop()
                    defer.returnValue(3)
                    return
            except Exception, e:
                self.debug("Failed to add: %r", log.getExceptionMessage(e))
                failed.append((path, e))
                continue

            if res:
                existing, new = res
                if existing:
                    self.stdout.write('Added to %d existing track(s).\n' %
                        len(existing))
                if new:
                    self.stdout.write('Created %d new track(s).\n' %
                        len(new))
            else:
                self.stdout.write('Audio file already in database.\n')

            # now chromaprint
            # FIXME: decide if this is how we want to delegate chromaprinting?
            c = self.parentCommand.subCommands['chromaprint']
            yield c.doLater([path, ])


        if failed:
            for path, e in failed:
                self.stdout.write('Failed to add %s:\n' % path.encode('utf-8'))
                self.stdout.write('%s\n' % log.getExceptionMessage(e))

class Chromaprint(tcommand.TwistedCommand):
    """
    @type hostname: unicode
    """

    description = """Chromaprint an audio file in the database."""
    hostname = None

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
            self.stderr.write('Please give path to chromaprint.\n')
            defer.returnValue(3)
            return

        interactor = database.DatabaseInteractor(
            self.parentCommand.database,
            self.parentCommand.runner)

        # FIXME: database-specific, should be replaced by more generic things
        # FIXME: imports reactor
        from twisted.web import error

        paths = common.expandPaths(args, self.stderr)

        failed = []
        for path in paths:
            path = os.path.abspath(path)
            self.stdout.write('%s\n' % path.encode('utf-8'))

            try:
                res = yield interactor.chromaprint(path, hostname=self.hostname)
            except error.Error, e:
                if e.status == 404:
                    self.stderr.write('Database or view does not exist.\n')
                    self.reactor.stop()
                    defer.returnValue(3)
                    return
            except Exception, e:
                failed.append((path, log.getExceptionMessage(e)))
                continue

            found = False
            for r in res:
                found = True
                print r
            if not found:
                self.stdout.write('%s not in database.\n' %
                    path.encode('utf-8'))


        if failed:
            for path, message in failed:
                self.stdout.write('Failed to chromaprint %s:\n' %
                    path.encode('utf-8'))
                self.stdout.write('%s\n' % message)


class Lookup(tcommand.TwistedCommand):
    description = """Look up audio files in the database."""

    @defer.inlineCallbacks
    def doLater(self, args):
        if not args:
            self.stderr.write('Please give paths to look up.\n')
            defer.returnValue(3)
            return


        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue
        
            self.stdout.write('%s\n' % path)
            try:
                ret = yield self.parentCommand.database.getTracksByHostPath(common.hostname(), path)
            except error.Error, e:
                if e.status == 404:
                    self.stderr.write('Database or view does not exist.\n')
                    self.reactor.stop()
                    defer.returnValue(3)
                    return

            ret = list(ret)
            if len(ret) == 0:
                self.stdout.write('Not in database.\n')
            else:
                self.stdout.write('In database in %d tracks.\n' % len(ret))
 

class Database(logcommand.LogCommand):

    """
    @type database: an implementor of L{idad.Database}
    @ivar database: the database selected
    """

    subCommandClasses = [Add, Chromaprint, track.Track, Lookup, score.Score,
        category.Category,
        selection.Selection]

    description = 'Interact with database backend.'

    database = None

    def _getProviders(self):
        from dad import plugins

        providers = {}
        for provider in plugin.getPlugins(idad.IDatabaseProvider, plugins):
            providers[provider.name] = provider
        return providers


    def addOptions(self):
        self.parser.add_option('-d', '--database',
                          action="store", dest="database",
                          help="select database and arguments (from %s, defaults to %s)" % (
                            ", ".join(self._getProviders().keys()), "couchdb"),
                          default="couchdb") # FIXME: don't hardcode?

    def handleOptions(self, options):
        
        providers = self._getProviders()

        args = []
        dbName = options.database

        if ':' in dbName:
            dbName, line = options.database.split(':', 1)
            args = line.split(':')

        if dbName not in providers.keys():
            self.stderr.write('Please choose an existing database.\n')
            self.stderr.write('Possible choices: %s\n' %
                ', '.join(providers.keys()))
            return

        provider = providers[dbName]

        parser = optparse.OptionParser()
        parser.usage = "-D %s:[option]:[option]:..." % dbName
        parser.add_options(provider.getOptions())

        if 'help' in args:
            self.stdout.write('Options for database %s:\n' % dbName)
            self.stdout.write(parser.format_option_help())
            return -3


        options, rest = parser.parse_args(args)

        if rest:
            self.stderr.write(
                "WARNING: make sure you specify options with dashes.\n")
            self.stderr.write("Did not parse %r\n" % rest)

        self.debug('Creating database %r with args %r',
            dbName, args)

        database = provider.getDatabase(options)
        self.database = database

        self.runner = task.SyncRunner()
