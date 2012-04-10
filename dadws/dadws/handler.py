# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
from datetime import datetime
import urllib

from twisted.web import resource, static

from dad.common import log

from dadws.extern.websocket import websocket

class MediaResource(resource.Resource):

    def __init__(self, player):
        self._player = player
        resource.Resource.__init__(self)

    def getChildWithDefault(self, path, request):
        fullPath = os.path.join('/', path, *request.postpath)

        if not os.path.exists(fullPath):
            print 'THOMAS: 404'
            return None # 404

        if not self._player.isAllowed(fullPath):
            print 'THOMAS: 401'
            return None # 401

        f = static.File(fullPath)
        # setting isLeaf makes sure that the resource exists;
        # no idea why that isn't the default for a file though
        f.isLeaf = 1
        #f.getChild = lambda p, r: traceback.print_stack()
        #import code; code.interact(local=locals())
        return f
        


class PlayerTestHandler(websocket.WebSocketHandler, log.Loggable):

    logCategory = 'wshandler'

    def __init__(self, transport, player, port):
        websocket.WebSocketHandler.__init__(self, transport)
        self._player = player
        self._port = port
        self.debug('handler: init')
        self._started = 0L

    # FIXME: remove
    def __del__(self):
        print 'Deleting handler'

    def started(self, started):
        self._started = started # epoch seconds
        self.debug('started time %r', started)

    def send_time(self):
        # send current time as an ISO8601 string
        data = datetime.utcnow().isoformat().encode('utf8')
        self.transport.write(data)


    def _send(self, **kwargs):
        import json
        self.transport.write(json.dumps(kwargs))


    def load_track(self, uri, id, **kwargs):
        """
        Tell the browser to load the given track.
        """
        self._send(command='load', uri=uri, id=id, **kwargs)

    # FIXME: not being used ?
    def play_track(self, id, when=None):
        """
        Tell the browser to schedule playing the given track
        at the given time.

        @param when: absolute time in epoch seconds.
        @type  when: float
        """
        self._send(command='play', id=id, when=self._started + when)


    def frameReceived(self, frame):
        self.debug('Peer: %r', self.transport.getPeer())
        # self.transport.write(frame)
        print 'received frame', frame
        import json
        received = json.loads(frame)
        if 'command' in received:
            method = getattr(self, 'receive_' + received['command'])
            del received['command']
            print 'received', received
            method(**received)

    def receive_reschedule(self, since, flavor=None):
        print 'ask scheduler to reschedule', since, flavor
        self._player.reschedule(since, flavor)

    def schedule(self, scheduled):
        path = '/media' + urllib.quote(scheduled.path.encode('utf-8'))
        when = self._started + \
            scheduled.start / float(1000 * 1000 * 1000), # ns -> s
        
        self.load_track(path, scheduled.number,
            artists=scheduled.artists, title=scheduled.title,
            when=when,
            offset=scheduled.mediaStart / float(1000 * 1000 * 1000),
            volume=scheduled.volume)


    def setFlavors(self, flavors):
        # tell the client about the flavors he can select
        self._send(command='setFlavors', flavors=flavors)

    def connectionMade(self):
        self.debug('Connected to client.')
        # here would be a good place to register this specific handler
        # in a dictionary mapping some client identifier (like IPs) against
        # self (this handler object)
        self._player.addClient(self)

    def connectionLost(self, reason):
        self.debug('Lost connection.')
        # here is a good place to deregister this handler object
