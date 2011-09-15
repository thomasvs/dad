# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from datetime import datetime


from dadws.extern.websocket import websocket

class PlayerTestHandler(websocket.WebSocketHandler):
    def __init__(self, transport, player):
        websocket.WebSocketHandler.__init__(self, transport)
        self._player = player

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
        self.transport.write(frame)

    def schedule(self, scheduled):
        
        self.load_track(scheduled.path, scheduled.number,
            artists=scheduled.artists, title=scheduled.title,
            when=scheduled.start,
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
