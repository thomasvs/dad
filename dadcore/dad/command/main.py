# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The main entry point for the 'dad' command-line application.
"""

import sys

from twisted import plugin

from dad import idad

from dad.common import log
from dad.common import logcommand
from dad.command import test, tcommand
from dad.task import md5task
from dad.command import database

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


class Dad(tcommand.LogReactorCommand):
    usage = "%prog %command"
    description = """DAD is a digital audio database.

DAD gives you a tree of subcommands to work with.
You can get help on subcommands by using the -h option to the subcommand.
"""

    subCommandClasses = [database.Database, MD5, test.Test, ]

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
        log.debug("dad", "parsing command line: dad %s" % " ".join(argv))
        return tcommand.LogReactorCommand.parse(self, argv)

