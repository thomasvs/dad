# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys
import random
import optparse

import pickle

import gobject
gobject.threads_init()

from twisted.python import reflect

from dad.audio import mixing, common
from dad.extern.log import log



class Main(log.Loggable):
    def __init__(self, loop):
        self._loop = loop # main loop

    def _setup_dbus(self):
        # dbussy bits

        def signal_handler(*keys):
            for key in keys:
                self.debug('Key %r pressed', key)
                if key == u'Next':
                    self.info('Next track')
                elif key == u'Play':
                    self.info('Play')
                    if self._playing:
                        self._pipeline.set_state(gst.STATE_PAUSED)
                        self._playing = False
                    else:
                        self._pipeline.set_state(gst.STATE_PLAYING)
                        self._playing = True

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
            import gtk

            w = gtk.Window()
            from dad.ui import scheduler as sch
            s = sch.SchedulerUI()

            def jukebox_started_cb(jukebox, scheduled):
                s.started(scheduled)
            self._jukebox.connect('started', jukebox_started_cb)

            def scheduler_clicked_cb(scheduler, scheduled):
                print 'seeking to %r' % scheduled
                where = scheduled.start
                self._pipeline.seek_simple(gst.FORMAT_TIME, 0, where)
            s.connect('clicked', scheduler_clicked_cb)

            s.set_scheduler(self._scheduler)

            sw = gtk.ScrolledWindow()
            sw.add(s)
            w.add(sw)
            w.set_default_size(640, 480)
            w.show_all()


    # FIXME: gtk frontend should be some kind of viewer class
    def setup(self, options):
        import gst

        from dadgst.gstreamer import jukebox
        from dad.common import scheduler, selecter

        _TEMPLATE = gst.PadTemplate('template', gst.PAD_SINK, gst.PAD_ALWAYS,
            gst.caps_from_string('audio/x-raw-int; audio/x-raw-float'))

        # parse selecter class and arguments

        selecterArgs = []
        selecterClassName = options.selecter

        if ':' in options.selecter:
            selecterClassName, line = options.selecter.split(':', 1)
            selecterArgs = line.split(' ')
        selecterClass = reflect.namedAny(selecterClassName)
        parser = selecterClass.option_parser_class()
        self.debug('Creating selecter %r with args %r',
            selecterClass, selecterArgs)

        if 'help' in selecterArgs:
            print 'Options for selecter %s' % selecterClassName
            parser.print_help()
            return False

        selOptions, selArgs = parser.parse_args(selecterArgs)
        self._selecter = selecterClass(selOptions)
        
        #sel = selecter.SimplePlaylistSelecter(
        #    tracks, options.playlist, options.random, loops=int(options.loops))
        self._scheduler = scheduler.Scheduler(self._selecter,
            begin=options.begin)
        self._jukebox = jukebox.JukeboxSource(self._scheduler)
        self._pipeline = gst.Pipeline()
        self._playing = False

        if options.gtk == True:
            self._setup_gtk()

        self._setup_dbus()


        self._identity = gst.element_factory_make('identity')
        # self._identity.connect('notify::last-message',
        #    lambda o, a: sys.stdout.write(
        #        '%r\n' % self._identity.props.last_message))
        self._identity.props.single_segment = True

        ac = gst.element_factory_make('audioconvert')
        queue = gst.element_factory_make('queue')
        
        # parse the sink as a bin, linking to the unconnected pad
        sink = gst.parse_launch('bin. ( %s )' % options.sink)
        # FIXME: changed to find_unlinked_pad in gstreamer 0.10.20
        pad = sink.find_unconnected_pad(gst.PAD_SINK)
        gpad = gst.GhostPad('ghost', pad)
        sink.add_pad(gpad)

        self._pipeline.add(self._jukebox, ac, self._identity, queue, sink)
        self._jukebox.link(ac)
        ac.link(self._identity)
        self._identity.link(queue)
        queue.link(sink)

        # pick songs

        for i in range(int(options.count)):
            path, track = self._selecter.get()
            self._scheduler.add_track(path, track)

        # setup succeeded
        return True


    def start(self):
        import gst
        print 'starting'
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._message_cb)
        self._pipeline.set_state(gst.STATE_PLAYING)
        self._playing = True
        print 'started'
        gobject.timeout_add(500, self._jukebox.work)
        gobject.timeout_add(500, self.work)

    def work(self):
        import gst
        pad = self._identity.get_pad('src')
        res = pad.query_position(gst.FORMAT_TIME)
        if res:
            position, format = res
            sys.stdout.write('\roverall position: %s' % 
                gst.TIME_ARGS(position))
            sys.stdout.flush()
        else:
            print 'Could not get position'
            sys.stdout.flush()

        return True
  

    def _message_cb(self, bus, message):
        if message.src == self._pipeline:
            self.debug('message from pipeline: %r', message)
        elif message.src == self._identity:
            self.debug('message from identity: %r', message)

def main():
    log.init('DAD_DEBUG')

    parser = optparse.OptionParser()

    default = 10
    parser.add_option('-c', '--count',
        action="store", dest="count",
        help="how many tracks to play (defaults to %d)" % default,
        default=default)
    default = -1
    # FIXME: should we proxy this to selecter or throw out ?
    parser.add_option('-l', '--loops',
        action="store", dest="loops",
        help="how many times to loop the playlist (defaults to %d)" % default,
        default=default),
    parser.add_option('-r', '--random',
        action="store_true", dest="random",
        help="play tracks in random order")
    default = 'queue ! autoaudiosink'
    parser.add_option('-s', '--sink',
        action="store", dest="sink",
        help="GStreamer audio sink to output to (defaults to %s" % default,
        default=default)
    parser.add_option('-b', '--begin',
        action="store_true", dest="begin",
        help="Start at beginning of first song, instead of before first mix")

    default = 'dad.common.selecter.SimplePlaylistSelecter'
    parser.add_option('', '--selecter',
        action="store", dest="selecter",
        help="Selecter class to use (default %s)" % default,
        default=default)

    parser.add_option('-g', '--gtk',
        action="store_true", dest="gtk",
        help="whether to use GTK+ (defaults to %default)",
        default=False)
 
    options, args = parser.parse_args(sys.argv[1:])

    import pygst
    pygst.require("0.10")

    loop = gobject.MainLoop()

    main = Main(loop)
    if not main.setup(options):
        return -1

    main.start()
    print 'going into main loop'
    loop.run()

    return 0

sys.exit(main())
