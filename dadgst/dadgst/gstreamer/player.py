# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import gobject
import optparse

from dad.common import player


_DEFAULT_SINK = 'queue ! autoaudiosink'
gst_player_option_list = [
    optparse.Option('-s', '--sink',
        action="store", dest="sink",
        help="GStreamer audio sink to output to (defaults to %default)",
        default=_DEFAULT_SINK),
]

# FIXME: is a Controller
class GstPlayer(player.Player):

    def __init__(self, scheduler):
        player.Player.__init__(self, scheduler)

        from dadgst.gstreamer import jukebox

        self._jukebox = jukebox.JukeboxSource(self.scheduler)

        self._scheduled = [] # (time, scheduled)

        self._jukebox.connect('started', self._jukebox_started_cb)

    def _jukebox_started_cb(self, jukebox, scheduled):
        self.doViews('scheduled_started', scheduled)

    def setup(self, options):

        sink = options.sink
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
        self.doViews('set_schedule_position', position)

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
