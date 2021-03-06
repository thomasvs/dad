# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import time

import urllib
import optparse

from twisted.internet import defer
from dad.common import player

SCHEDULE_DURATION = 1200L # in seconds

_DEFAULT_PORT = 8888

ws_player_option_list = [
    optparse.Option('-p', '--port',
        action="store", dest="port",
        help="WebSocket port (defaults to %default)",
        default=_DEFAULT_PORT),
]

class WebSocketPlayer(player.Player):

    logCategory = 'wsplayer'

    def __init__(self, scheduler):
        player.Player.__init__(self, scheduler)

        self._scheduled = [] # (time, scheduled)

        self._scheduler = scheduler
        self._clients = []

        self._lastend = 0L
        self._started = 0L # seconds since epoch when we started

        self._scheduling = False

        self.url = None

    def setup(self, options):

        port = int(options.port)
        self.debug('setup: going to listen on port %d', port)

        from twisted.internet import reactor

        # run our websocket server
        path = os.path.join(os.path.dirname(__file__), 'www')
        from twisted.web.static import File
        root = File(path)

        from dadws import handler
        from dadws.extern.websocket import websocket
        site = websocket.WebSocketSite(root)
        site.addHandler('/test', lambda transport:
            handler.PlayerTestHandler(transport, self, port))
        # add songs ?
        self._media = handler.MediaResource(self)
        root.putChild('media', self._media)

        p = reactor.listenTCP(port, site)
        self.debug('setup: listening on port %d', p.port)
        self.url = 'http://localhost:%d' % p.port

    def start(self):
        self._started = time.time()
        for client in self._clients:
            client.started(self._started)
        self._scheduler.schedule()
        from twisted.internet import reactor
        reactor.callLater(0L, self.keepScheduled)

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
        self._scheduling = False
        self.debug('scheduled %r', scheduled)
        self._scheduled.append((scheduled.start, scheduled)) 
        for client in self._clients:
            client.schedule(scheduled)
        self._lastend = scheduled.start + scheduled.duration
        # make it available for download
        from twisted.web import static
        self.debug('publishing path %r', scheduled.path)
        # FIXME: putChild with nested path does not seem to work
        uri = urllib.quote(scheduled.path.encode('utf-8'))
        c = self._media.putChild(uri, static.File(scheduled.path))
        self.debug('published as %s/media%s', self.url, uri)

    @defer.inlineCallbacks
    def addClient(self, transport):
        self.debug('addClient: %r', transport)
        self._clients.append(transport)
        transport.started(self._started)
        for _, scheduled in self._scheduled:
            # only schedule tracks that shouldn't have finished yet
            now = time.time()
            # FIXME: should probably keep a small window for tracks
            # in the middle of playing
            if self._started + nsToS(scheduled.start + scheduled.duration) < now:
                continue
            self.debug('Scheduling %r', scheduled)
            transport.schedule(scheduled)

        # send flavors
        flavors = yield self._scheduler.getFlavors()
        transport.setFlavors(flavors)


    # specific methods
    def isAllowed(self, path):
        for _, scheduled in self._scheduled:
            if scheduled.path.encode('utf-8') == path:
                return True

        return False

    # keeping things scheduled
    def keepScheduled(self):
        from twisted.internet import reactor
        remaining = nsToS(self._lastend) - self.position()
        self.debug('keepScheduled: %.3f s remaining', remaining)
        if remaining < SCHEDULE_DURATION:
            self.debug('Need to schedule some more')
            # only ask once at a time
            if not self._scheduling:
                self.info('asking scheduler to schedule')
                self._scheduling = True
                self._scheduler.schedule()

        # FIXME: instead of always calling this again, wait for the result
        # of the previous schedule, but keep scheduling
        reactor.callLater(10L, self.keepScheduled)

    def reschedule(self, since, category=None):
        self._scheduler.reschedule(since, category)
        # FIXME: _lastend ?

    def position(self):
        return time.time() - self._started

def nsToS(ns):
    return float(ns) / (1000.0 * 1000 * 1000)
