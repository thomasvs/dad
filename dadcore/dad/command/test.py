# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The entry point for test applications.
"""

import optparse

from dad import idad

from dad.base import app
from dad.common import log
from dad.common import logcommand
from dad.command import tcommand

class Artist(tcommand.TwistedCommand):

    description = """Test viewing artists."""

    def installReactor(self):
        from dadgtk.twisted import gtk2reactor
        gtk2reactor.install()
        tcommand.TwistedCommand.installReactor(self)

    def done_cb(self, _):
        self._doneDeferred.callback(None)

    def doLater(self, args):

        # FIXME: view-specific
        import gtk

        from twisted.python import reflect
        from twisted.internet import defer
        defer.Deferred.debug = 1

        self._doneDeferred = defer.Deferred()

        # FIXME: allow customizing model and/or view(s)
        viewTypes = ['GTK', ]

        db = self.parentCommand.getDatabase()
        self.debug('Database: %r', db)


        # get the model
        amodel = self.parentCommand.getAppModel()
        self.debug('App model: %r', amodel)

        acontroller = app.AppController(amodel)

        for viewType in viewTypes:
            viewModule = 'dad%s.views.app.%sAppView' % (viewType.lower(), viewType)
            aview = reflect.namedAny(viewModule)()
            acontroller.addView(aview)


        # FIXME: gtk-specific
        aview.widget.connect('destroy', self.done_cb)


        vbox = gtk.VBox()

        hbox = gtk.HBox()

        vbox.add(hbox)

        aview.widget.add(vbox)

        asController, asModel, asViews = acontroller.getTriad('ArtistSelector')

        hbox.pack_start(asViews[0])


        aview.widget.show_all()


        # start loading artists and albums

        d = defer.Deferred()
        d.addCallback(lambda _: log.debug('test', 'asking controller to populate'))

        d.addCallback(lambda _: asController.populate())

        d.callback(None)

        return self._doneDeferred


class Test(logcommand.LogCommand):

    """
    @type database: an implementor of L{idad.Database}
    @ivar database: the database selected
    """

    subCommandClasses = [Artist, ]

    description = 'Run test applications'
    database = None

    def _getProviders(self):
        from twisted import plugin
        from dad import plugins

        providers = {}
        for provider in plugin.getPlugins(idad.IDatabaseProvider, plugins):
            providers[provider.name] = provider
        return providers


    def addOptions(self):
        self.parser.add_option('-d', '--database',
                          action="store", dest="database",
                          default="couchdb", # FIXME: don't hardcode?
                          help="select database and arguments (from %s)" % (
                            ", ".join(self._getProviders().keys())))

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


        self._dbOptions, rest = parser.parse_args(args)

        if rest:
            self.stderr.write(
                "WARNING: make sure you specify options with dashes.\n")
            self.stderr.write("Did not parse %r\n" % rest)

        self._provider = provider


    def getDatabase(self):
        # Implemented as a method so it's instantiated lazily and the
        # reactor does not get imported because of paisley.client

        if not self.database:
            self.debug('Creating database %r with args %r',
                self._provider, self._dbOptions)
            self.database = self._provider.getDatabase(self._dbOptions)

        return self.database

    def getAppModel(self):
        return self._provider.getAppModel(self.getDatabase())
