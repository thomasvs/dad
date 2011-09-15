# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
The entry point for test applications.
"""

import optparse

from twisted.internet import defer
from twisted.python import reflect
from twisted import plugin

from dad import idad

from dad.base import app
from dad.common import log
from dad.common import logcommand
from dad.command import tcommand

from dadgtk.views import player as vplayer


class Gtk2Command(tcommand.TwistedCommand):
    def installReactor(self):
        from dadgtk.twisted import gtk2reactor
        gtk2reactor.install()
        tcommand.TwistedCommand.installReactor(self)


class Artist(Gtk2Command):

    description = """Test viewing artists."""

    def done_cb(self, _):
        self._doneDeferred.callback(None)

    def doLater(self, args):

        # FIXME: view-specific
        import gtk

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

class JukeboxMain(log.Loggable):

    def _setup_dbus(self):
        # dbussy bits

        def signal_handler(*keys):
            for key in keys:
                self.debug('Key %r pressed', key)
                if key == u'Next':
                    self.info('Next track')
                    self._player.next()
                if key == u'Previous':
                    self.info('Previous track')
                    self._player.previous()
                elif key == u'Play':
                    self.info('Play')
                    self._player.toggle()

        import dbus
        # this import has the side effect of setting the main loop on dbus
        from dbus import glib
        bus = dbus.SessionBus()
        try:
            listener = bus.get_object('org.gnome.SettingsDaemon',
                '/org/gnome/SettingsDaemon/MediaKeys')
            listener.connect_to_signal("MediaPlayerKeyPressed", signal_handler,
                dbus_interface='org.gnome.SettingsDaemon.MediaKeys')
        except Exception, e:
            print 'Cannot listen to multimedia keys', e

    def _setup_gtk(self):
            gtkui = vplayer.GTKPlayerView(self._player)
            #options FIXME: don't poke in privates
            self._player._uis.append(gtkui)


    # FIXME: gtk frontend should be some kind of viewer class
    def _getScheduler(self, options):
        from dad.common import scheduler
        # parse selecter class and arguments

        selecterArgs = []
        selecterClassName = options.selecter

        if ':' in options.selecter:
            selecterClassName, line = options.selecter.split(':', 1)
            selecterArgs = line.split(':')
        selecterClass = reflect.namedAny(selecterClassName)
        parser = selecterClass.option_parser_class()
        self.debug('Creating selecter %r with args %r',
            selecterClass, selecterArgs)

        if 'help' in selecterArgs:
            print 'Options for selecter %s' % selecterClassName
            parser.print_help()
            return defer.fail(False)

        selOptions, selArgs = parser.parse_args(selecterArgs)
        # FIXME: handle this nicer, too easy to hit
        if selArgs:
            print "WARNING: make sure you specify options with dashes"
            print "Did not parse %r" % selArgs

        self._selecter = selecterClass(selOptions)
        
        #sel = selecter.SimplePlaylistSelecter(
        #    tracks, options.playlist, options.random, loops=int(options.loops))
        self._scheduler = scheduler.Scheduler(self._selecter,
            begin=options.begin)

        return self._scheduler

    def setup(self, options, playerOptions):

        if options.gtk == True:
            self._setup_gtk()

        self._setup_dbus()

        # now we can start triggering setup calls
        # FIXME: take all options, not just the one
        self._player.setup(playerOptions.sink)


        # FIXME: async setup selecter, then start selecting
        d = self._selecter.setup()

        #for i in range(int(options.count)):
        #    print self._selecter.get()
        #    path, track = self._selecter.get()
        #    self._scheduler.add_track(path, track)
        # finally return True if setup succeeded
        d.addCallback(lambda _: True)

        return d


    def start(self):
        self._player.start()


# FIXME: install reactor optionally only ?
class Jukebox(Gtk2Command):
    description = """Test the whole selector."""

    # FIXME: extract and reuse ?
    def _getProviders(self):
        from dad import plugins

        providers = {}
        for provider in plugin.getPlugins(idad.IPlayerProvider, plugins):
            providers[provider.name] = provider
        return providers


    def addOptions(self):
        default = 10
        self.parser.add_option('-c', '--count',
            action="store", dest="count",
            help="how many tracks to play (defaults to %default)",
            default=default)
        default = -1
        # FIXME: should we proxy this to selecter or throw out ?
        self.parser.add_option('-l', '--loops',
            action="store", dest="loops",
            help="how many times to loop the playlist (defaults to %default)",
            default=default),
        self.parser.add_option('-r', '--random',
            action="store_true", dest="random",
            help="play tracks in random order")
        self.parser.add_option('-b', '--begin',
            action="store_true", dest="begin",
            help="Start at beginning of first song, instead of before first mix")

        default = 'dad.common.selecter.SimplePlaylistSelecter'
        self.parser.add_option('', '--selecter',
            action="store", dest="selecter",
            help="Selecter class to use (default %default)",
            default=default)

        self.parser.add_option('-g', '--gtk',
            action="store_true", dest="gtk",
            help="whether to use GTK+ (defaults to %default)",
            default=False)
     
        self.parser.add_option('-p', '--player',
                          action="store", dest="player",
                          default="gst", # FIXME: don't hardcode?
                          help="select player and arguments (from %s)" % (
                            ", ".join(self._getProviders().keys())))

    def handleOptions(self, options):
        
        self._main = JukeboxMain()

        providers = self._getProviders()

        # FIXME: abstract this code
        args = []
        playerName = options.player

        if ':' in playerName:
            playerName, line = options.player.split(':', 1)
            args = line.split(':')

        if playerName not in providers.keys():
            self.stderr.write('Please choose an existing player.\n')
            self.stderr.write('Possible choices: %s\n' %
                ', '.join(providers.keys()))
            return

        provider = providers[playerName]

        parser = optparse.OptionParser()
        parser.usage = "--player %s:[option]:[option]:..." % playerName
        parser.add_options(provider.getOptions())

        if 'help' in args:
            self.stdout.write('Options for player %s:\n' % playerName)
            self.stdout.write(parser.format_option_help())
            return -3


        playerOptions, rest = parser.parse_args(args)

        if rest:
            self.stderr.write(
                "WARNING: make sure you specify options with dashes.\n")
            self.stderr.write("Did not parse %r\n" % rest)

        self.debug('Creating player %r with args %r',
            playerName, args)

        self._playerProvider = provider
        self._playerOptions = playerOptions

    def doLater(self, args):
        scheduler = self._main._getScheduler(self.options)

        player = self._playerProvider.getPlayer(scheduler, self._playerOptions)
        self.player = player


        main = self._main
        # FIXME: ugly proxying
        self._main._player = player

        d = main.setup(self.options, self._playerOptions)
        def setupCb(result):
            if not result:
                from twisted.internet import reactor
                print 'setup failed, stopping reactor'
                reactor.callLater(0L, reactor.stop)

            print 'calling main.start'
            ret = main.start()

            # FIXME: exit properly when user quits
            return defer.Deferred()

        def setupEb(failure):
            from twisted.internet import reactor
            reactor.callLater(0L, reactor.stop)

        d.addCallback(setupCb)
        d.addErrback(setupEb)

        return d

class Selector(Gtk2Command):

    description = """Test the whole selector."""

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

        alsController, alsModel, alsViews = acontroller.getTriad('AlbumSelector')
        hbox.pack_start(alsViews[0])

        tController, tModel, tViews = acontroller.getTriad('TrackSelector')

        vbox.add(tViews[0])

        aview.widget.show_all()


        # listen to changes on artist selection so we can filter
        # the albums and tracks selector views
        def artist_selected_cb(self, ids):
            self.debug('artist_selected_cb: ids %r', ids)

            # without ids, select everything
            album_ids = None

            if ids is not None:
                album_ids = alsModel.get_artists_albums(ids)

            alsViews[0].set_album_ids(album_ids)

            tViews[0].set_artist_ids(ids)

        asViews[0].connect('selected', artist_selected_cb)

        # listen to changes on album selection so we can filter
        # the tracks selector view
        # FIXME: not finished and hooked up!
        def album_selected_cb(self, ids):
            self.debug('album_selected_cb: ids %r', ids)

            # without ids, select everything
            track_ids = None

            if ids is not None:
                track_ids = alsModel.get_albums_tracks(ids)

            tViews[0].set_album_ids(ids)

        #alViews[0].connect('selected', album_selected_cb)


        def track_selected_cb(self, trackObj):
            w = gtk.Window()


            self.debug('clicked on track %r', trackObj)
            tController, tModel, tViews = acontroller.getTriad('Track')

            # FIXME: don't hardcode
            user = 'thomas'
            d = tController.populate(trackObj, userName=user)
            d.addCallback(lambda _, o: o.getName(), trackObj)
            d.addCallback(lambda n: w.set_title(n))
            w.add(tViews[0].widget)

            w.show_all()
     

        tViews[0].connect('clicked', track_selected_cb)

        # start loading artists and albums

        d = defer.Deferred()

        d.addCallback(lambda _: asController.populate())
        d.addCallback(lambda _: alsController.populate())
        d.addCallback(lambda _: tController.populate())

        d.callback(None)

        return self._doneDeferred

class Test(logcommand.LogCommand):

    """
    @type database: an implementor of L{idad.Database}
    @ivar database: the database selected
    """

    subCommandClasses = [Artist, Selector, Jukebox]

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
