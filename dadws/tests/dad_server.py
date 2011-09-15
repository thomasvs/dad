""" WebSocket test resource.

This code will run a websocket resource on 8080 and reachable at ws://localhost:8080/test.
For compatibility with web-socket-js (a fallback to Flash for browsers that do not yet support
WebSockets) a policy server will also start on port 843.
See: http://github.com/gimite/web-socket-js
"""

__author__ = 'Reza Lotun'


from datetime import datetime
import os

from twisted.web.static import File

from dadws.extern.websocket.websocket import WebSocketHandler, WebSocketSite
from dadws.extern.websocket import websocket

class Testhandler(WebSocketHandler):
    def __init__(self, transport):
        WebSocketHandler.__init__(self, transport)

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

        uri = 'http://localhost:8080/daughters.ogg'
        self.load_track(uri, 1, artist='The National',
            title='Daughters of the Soho Riots', when=5)

        uri = 'http://localhost:8080/abel.ogg'
        reactor.callLater(2L, self.load_track, uri, 2, artist='The National',
            title='Abel', when=15)

    def connectionMade(self):
        print 'Connected to client.'
        # here would be a good place to register this specific handler
        # in a dictionary mapping some client identifier (like IPs) against
        # self (this handler object)

    def connectionLost(self, reason):
        print 'Lost connection.'
        # here is a good place to deregister this handler object


if __name__ == "__main__":
    from twisted.internet import reactor

    # run our websocket server
    # serve index.html from the local directory
    # path = os.path.dirname(websocket.__file__)
    path = os.path.dirname(__file__)
    root = File(path)
    site = WebSocketSite(root)
    site.addHandler('/test', Testhandler)
    root.putChild("16.mp3", File("/tmp/16.mp3"))
    root.putChild("blood", File("/tmp/blood.mp3"))
    root.putChild("abel.ogg", File("/tmp/abel.ogg"))
    root.putChild("daughters.ogg", File("/tmp/daughters.ogg"))
    reactor.listenTCP(8080, site)

    reactor.run()

