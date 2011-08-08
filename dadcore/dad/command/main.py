# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys

from twisted import plugin

from dad import idad

from dad.common import log
from dad.common import logcommand

from dad.extern.command import command


def main(argv):

    # import command plugins

    from dad import plugins
    for commander in plugin.getPlugins(idad.ICommand, plugins):
        commander.addCommands(Dad)

    c = Dad()

    try:
        ret = c.parse(argv)
    except SystemError, e:
        sys.stderr.write('rip: error: %s\n' % e.args)
        return 255
    except ImportError, e:
        # FIXME: decide how to handle
        raise
        # deps.handleImportError(e)
    except command.CommandError, e:
        sys.stderr.write('rip: error: %s\n' % e.output)
        return e.status

    if ret is None:
        return 0

    return ret

class Dad(logcommand.LogCommand):
    usage = "%prog %command"
    description = """DAD is a digital audio database.

DAD gives you a tree of subcommands to work with.
You can get help on subcommands by using the -h option to the subcommand.
"""

    subCommandClasses = []

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

