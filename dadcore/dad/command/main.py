# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The main entry point for the 'dad' command-line application.
"""

import os
import sys
import optparse

from twisted import plugin

from twisted.internet import defer


from dad import idad

from dad.common import log
from dad.common import logcommand
from dad.command import test, tcommand, category
from dad.task import md5task
from dad.logic import database

from dad.extern.command import command
from dad.extern.task import task


def main(argv):

    # import command plugins

    from dad import plugins

    # no reactor yet
    # from twisted.internet import glib2reactor; glib2reactor.install(); sys.exit(0)
    for commander in plugin.getPlugins(idad.ICommand, plugins):
        commander.addCommands(Dad)

    c = Dad()

    try:
        ret = c.parse(argv)
    except SystemError, e:
        sys.stderr.write('dad: error: %s\n' % e.args)
        return 255
    except ImportError, e:
        # FIXME: decide how to handle
        raise
        # deps.handleImportError(e)
    except command.CommandError, e:
        sys.stderr.write('dad: error: %s\n' % e.output)
        return e.status

    if ret is None:
        return 0

    return ret

def _hostname():
    import socket
    return unicode(socket.gethostname())


def _expandPaths(args, stderr):
    paths = []

    for path in args:
        path = path.decode('utf-8')
        if not os.path.exists(path):
            stderr.write('Could not find %s\n' % path.encode('utf-8'))
            continue

        # handle playlist
        if path.endswith('.m3u'):
            handle = open(path, 'r')
            for line in handle.readlines():
                if line.startswith('#'):
                    continue
                filePath = line.decode('utf-8').strip()
                if not os.path.exists(filePath):
                    stderr.write('Could not find %s\n' %
                        filePath.encode('utf-8'))
                    continue
                paths.append(filePath)
        else:
            paths.append(path)

    return paths


class List(tcommand.TwistedCommand):

    @defer.inlineCallbacks
    def doLater(self, args):
        db = self.parentCommand.database
        res = yield db.getTracks()
        for track in res:
            self.stdout.write('%s - %s\n' % (
                " & ".join(track.getArtistNames()), track.getName()))


class Add(tcommand.TwistedCommand):
    """
    @type hostname: unicode
    """

    description = """Add audio files to the database."""
    hostname = None

    def addOptions(self):
        self.parser.add_option('-H', '--hostname',
                          action="store", dest="hostname",
                          default=_hostname(),
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

        paths = _expandPaths(args, self.stderr)

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
                          default=_hostname(),
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

        paths = _expandPaths(args, self.stderr)

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
                failed.append((path, e))
                continue

            found = False
            for r in res:
                found = True
                print r
            if not found:
                self.stdout.write('%s not in database.\n' %
                    path.encode('utf-8'))


        if failed:
            for path, e in failed:
                self.stdout.write('Failed to chromaprint %s:\n' %
                    path.encode('utf-8'))
                self.stdout.write('%s\n' % log.getExceptionMessage(e))


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
                ret = yield self.parentCommand.database.getTracksByHostPath(_hostname(), path)
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

    subCommandClasses = [Add, Chromaprint, List, Lookup, category.Category]

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

class MD5(logcommand.LogCommand):
    summary = "calculate md5sum"

    def do(self, args):

        def later():
            d = self.doLater(args)
            # d.addCallback(lambda _: self.reactor.stop())

        self.reactor.callLater(0, later)

        self.reactor.run()

    def doLater(self, args):
        runner = task.SyncRunner()

        for path in args:
            path = path.decode('utf-8')
            t = md5task.MD5Task(path)
            runner.run(t)
            self.stdout.write('%s %s\n' % (t.md5sum, path.encode('utf-8')))

        self.reactor.stop()


class Dad(logcommand.LogCommand):
    usage = "%prog %command"
    description = """DAD is a digital audio database.

DAD gives you a tree of subcommands to work with.
You can get help on subcommands by using the -h option to the subcommand.
"""

    subCommandClasses = [Database, MD5, test.Test, ]

    def addOptions(self):
        # FIXME: is this the right place ?
        log.init()
        # from dad.configure import configure
        log.debug("dad", "This is dad version %s (%s)", "0.0.0", "0")
        #    configure.version, configure.revision)

        self.parser.add_option('-v', '--version',
                          action="store_true", dest="version",
                          help="show version information")

    def handleOptions(self, options):
        if options.version:
            from dad.configure import configure
            print "dad %s" % configure.version
            sys.exit(0)

    def parse(self, argv):
        log.debug("dad", "dad %s" % " ".join(argv))
        logcommand.LogCommand.parse(self, argv)

