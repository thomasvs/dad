# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys
import random
import optparse

import pickle

import gobject
gobject.threads_init()

from twisted.python import reflect
from twisted.internet import defer

from dad.audio import mixing, common
from dad.extern.log import log

from dad.common import player

class UI:
    """
    I am a base class for a UI.
    """
    def __init__(self, player):
        self._player = player

    def set_schedule_position(self, position):
        raise NotImplementedError

    def set_schedule_length(self, length):
        raise NotImplementedError

class CommandUI(UI):
    """
    I am a simple command-line application UI.
    """
    def __init__(self, player):
        self._player = player

    def set_schedule_position(self, position):
        if position is not None:
            import gst
            sys.stdout.write('\roverall position: %s' % 
                gst.TIME_ARGS(position))
            sys.stdout.flush()
        else:
            print 'Could not get position'
            sys.stdout.flush()

class GTKUI(UI):
    def __init__(self, player):

        self._player = player

        self._playing = None

        import gtk

        self._window = gtk.Window()
        from dad.ui import scheduler as sch, seek
        sui = sch.SchedulerUI()

        def jukebox_started_cb(jukebox, scheduled):
            sui.started(scheduled)
            import gst
            self._seekui.set_track_length(
                float(scheduled.duration) / gst.SECOND)
            self._seekui.set_track_offset(
                float(scheduled.start) / gst.SECOND)
            self._seekui.set_schedule_length(
                float(self._player.scheduler.duration) / gst.SECOND)
            self._playing = scheduled
            self._window.set_title('dad: %s - %s' % (
                " & ".join(scheduled.artists), scheduled.title))

        # FIXME: poking into private bits
        self._player._jukebox.connect('started', jukebox_started_cb)

        def scheduler_clicked_cb(scheduler, scheduled):
            print 'seeking to %r' % scheduled
            where = scheduled.start
            self._player.seek(where)
        sui.connect('clicked', scheduler_clicked_cb)

        sui.set_scheduler(player.scheduler)

        sw = gtk.ScrolledWindow()
        sw.add(sui)

        box = gtk.VBox()
        box.set_homogeneous(False)
        box.add(sw)

        self._seekui = seek.SeekUI()
        box.pack_end(self._seekui, expand=False, fill=False)

        def _seeked_schedule_cb(seekui, position):
            import gst
            self._player.seek(position * gst.SECOND)
        self._seekui.connect('seeked-schedule', _seeked_schedule_cb)
            

        self._window.add(box)

        self._window.set_default_size(640, 480)
        self._window.show_all()

    def set_schedule_position(self, position):
        import gst
        if position is not None:
            self._seekui.set_schedule_position(float(position) / gst.SECOND)
            if self._playing is not None:
                self._seekui.set_track_position(
                    float(position - self._playing.start) / gst.SECOND)


class GstPlayer(player.Player):

    def __init__(self, scheduler):
        player.Player.__init__(self, scheduler)

        from dadgst.gstreamer import jukebox

        self._jukebox = jukebox.JukeboxSource(self.scheduler)

        self._scheduled = [] # (time, scheduled)

        self._uis = [CommandUI(self), ]

    def setup(self, sink):

        import gst

        _TEMPLATE = gst.PadTemplate('template', gst.PAD_SINK, gst.PAD_ALWAYS,
            gst.caps_from_string('audio/x-raw-int; audio/x-raw-float'))

        self._pipeline = gst.Pipeline()
        self._playing = False

        self._identity = gst.element_factory_make('identity')
        # self._identity.connect('notify::last-message',
        #    lambda o, a: sys.stdout.write(
        #        '%r\n' % self._identity.props.last_message))
        self._identity.props.single_segment = True

        ac = gst.element_factory_make('audioconvert')
        queue = gst.element_factory_make('queue')
        
        # parse the sink as a bin, linking to the unconnected pad
        sink = gst.parse_launch('bin. ( %s )' % sink)
        # FIXME: changed to find_unlinked_pad in gstreamer 0.10.20
        pad = sink.find_unconnected_pad(gst.PAD_SINK)
        gpad = gst.GhostPad('ghost', pad)
        sink.add_pad(gpad)

        self._pipeline.add(self._jukebox, ac, self._identity, queue, sink)
        self._jukebox.link(ac)
        ac.link(self._identity)
        self._identity.link(queue)
        queue.link(sink)

        print 'make jukebox do work'
        self._jukebox.work()

    def start(self):
        import gst
        print 'starting pipeline and playback'
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._message_cb)
        self._pipeline.set_state(gst.STATE_PLAYING)
        self._playing = True
        print 'started'
        gobject.timeout_add(500, self._jukebox.work)
        gobject.timeout_add(500, self.work)

    def get_position(self):
        """
        Return the position, in nanoseconds.
        """
        import gst

        # FIXME: the src pad gives NONE during mixes, why ?
        pad = self._identity.get_pad('sink')
        res = pad.query_position(gst.FORMAT_TIME)
        if res:
            position, _ = res
            return position

        return None
 
    def work(self):
        position = self.get_position()
        for ui in self._uis:
            ui.set_schedule_position(position)

        return True


    def seek(self, where):
        import gst
        self.debug("Seek to %r", gst.TIME_ARGS(where))
        # FIXME: poking into private bits
        self._pipeline.seek_simple(gst.FORMAT_TIME, 0, where)
  
    def toggle(self):
        """
        Toggle between paused and playing, as a result of a UI event.
        """
        import gst
        if self._playing:
            self._pipeline.set_state(gst.STATE_PAUSED)
            self._playing = False
        else:
            self._pipeline.set_state(gst.STATE_PLAYING)
            self._playing = True

    def previous(self):
        """
        Skip to the previous song.
        """
        position = self.get_position()
        if position is None:
            print "Cannot get position so cannot go to next"
            return False

        # FIXME: search better
        import gst
        self.debug('previous: current position %r', gst.TIME_ARGS(position))
        r = self._scheduled[:]
        r.reverse()
        hit = 0
        for where, scheduled in r:
            if position > where:
                hit += 1
                # we want the track *before* the one where position is higher,
                # since that one is the currently playing track
                if hit == 2:
                    break

        if position < where:
            print "Cannot go back because at beginning"
            return False
            
        self.seek(where)

        self.debug('Previous, seeking to scheduled %r, where %r',
            scheduled, where)
        return True 


    def next(self):
        """
        Skip to the next song.
        """
        position = self.get_position()
        if position is None:
            print "Cannot get position so cannot go to next"
            return False

        # FIXME: search better
        import gst
        self.debug('next: current position %r', gst.TIME_ARGS(position))
        for where, scheduled in self._scheduled:
            if position < where:
                break

        if position > where:
            print "Cannot get position because no songs left"
            return False
            
        self.seek(where)

        self.debug('Next, seeking to scheduled %r, where %r',
            scheduled, where)
        return True 

    def scheduled_cb(self, scheduler, scheduled):
        self._scheduled.append((scheduled.start, scheduled)) 

    def _message_cb(self, bus, message):
        if message.src == self._pipeline:
            self.debug('message from pipeline: %r', message)
        elif message.src == self._identity:
            self.debug('message from identity: %r', message)



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
            gtkui = GTKUI(self._player)
            # FIXME: don't poke in privates
            self._player._uis.append(gtkui)


    # FIXME: gtk frontend should be some kind of viewer class
    def setup(self, options):
        from dad.common import scheduler, selecter
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
        self._player = GstPlayer(self._scheduler)

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
