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

    def __init__(self, transport, player, port):
        websocket.WebSocketHandler.__init__(self, transport)
        self._player = player
        self._port = port
        self.debug('handler: init')

    def __del__(self):
        print 'Deleting handler'

    def send_time(self):
        # send current time as an ISO8601 string
        data = datetime.utcnow().isoformat().encode('utf8')
        self.transport.write(data)


    def _send(self, **kwargs):
        import json
        self.transport.write(json.dumps(kwargs))


    def load_track(self, uri, id, **kwargs):
        self._send(command='load', uri=uri, id=id, **kwargs)

    def play_track(self, id, when=None):
        self._send(command='play', id=id, when=when)


    def frameReceived(self, frame):
        print 'Peer: ', self.transport.getPeer()
        # self.transport.write(frame)

    def schedule(self, scheduled):
        path = 'http://localhost:%d/media' % self._port + urllib.quote(scheduled.path)
        
        self.load_track(path, scheduled.number,
            artists=scheduled.artists, title=scheduled.title,
            when=scheduled.start / float(1000 * 1000 * 1000), # ns -> s
            offset=scheduled.mediaStart / float(1000 * 1000 * 1000),
            volume=scheduled.volume)



    def connectionMade(self):
        print 'Connected to client.'
        # here would be a good place to register this specific handler
        # in a dictionary mapping some client identifier (like IPs) against
        # self (this handler object)
        self._player.addClient(self)

    def connectionLost(self, reason):
        print 'Lost connection.'
        # here is a good place to deregister this handler object
