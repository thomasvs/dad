# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys
import optparse

import gobject
gobject.threads_init()

from twisted.python import reflect
from twisted.internet import defer

from dad.extern.log import log

from dadgtk.views import player as vplayer

from dadgst.gstreamer import player as gplayer


class Main(log.Loggable):

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
            # FIXME: don't poke in privates
            self._player._uis.append(gtkui)


    # FIXME: gtk frontend should be some kind of viewer class
    def setup(self, options):
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
        self._player = gplayer.GstPlayer(self._scheduler)

        if options.gtk == True:
            self._setup_gtk()

        self._setup_dbus()

        # now we can start triggering setup calls
        self._player.setup(options.sink)


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

def main():
    log.init('DAD_DEBUG')

    parser = optparse.OptionParser()

    default = 10
    parser.add_option('-c', '--count',
        action="store", dest="count",
        help="how many tracks to play (defaults to %default)",
        default=default)
    default = -1
    # FIXME: should we proxy this to selecter or throw out ?
    parser.add_option('-l', '--loops',
        action="store", dest="loops",
        help="how many times to loop the playlist (defaults to %default)",
        default=default),
    parser.add_option('-r', '--random',
        action="store_true", dest="random",
        help="play tracks in random order")
    parser.add_option('-b', '--begin',
        action="store_true", dest="begin",
        help="Start at beginning of first song, instead of before first mix")

    default = 'dad.common.selecter.SimplePlaylistSelecter'
    parser.add_option('', '--selecter',
        action="store", dest="selecter",
        help="Selecter class to use (default %default)",
        default=default)

    parser.add_option('-g', '--gtk',
        action="store_true", dest="gtk",
        help="whether to use GTK+ (defaults to %default)",
        default=False)
 
    parser.add_options(gplayer.gst_player_option_list)

    options, args = parser.parse_args(sys.argv[1:])

    import pygst
    pygst.require("0.10")

    from twisted.internet import gtk2reactor
    gtk2reactor.install()
    from twisted.internet import reactor

    main = Main()

    d = main.setup(options)

    def setupCb(result):
        if not result:
            print 'setup failed, stopping reactor'
            reactor.callLater(0L, reactor.stop)

        print 'calling main.start'
        return main.start()
    def setupEb(failure):
        reactor.callLater(0L, reactor.stop)

    d.addCallback(setupCb)
    d.addErrback(setupEb)


    print 'going into main loop'
    reactor.run()

    return 0

sys.exit(main())
