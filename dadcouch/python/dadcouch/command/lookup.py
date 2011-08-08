# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding couchdb-based functionality to dad command

import os

from twisted.internet import reactor
from twisted.internet import defer
from twisted.web import error

from dad.common import logcommand

from dadcouch.model import daddb
from dadcouch.selecter import couch

from dadcouch.extern.paisley import client


class Lookup(logcommand.LogCommand):
    description = """Look up audio files in the database."""

    def addOptions(self):
        self.parser.add_options(couch.couchdb_option_list)
    
    def do(self, args):
        self._db = client.CouchDB(self.options.host, int(self.options.port))
        self._daddb = daddb.DADDB(self._db, self.options.database)

        def later():
            d = self._doCb(args)
            d.addCallback(lambda _: reactor.stop())

        reactor.callLater(0, later)

        reactor.run()

    @defer.inlineCallbacks
    def _doCb(self, args):
        if not args:
            self.stderr.write('Please give paths to look up.\n')
            defer.returnValue(3)
            return

        import socket
        hostname = unicode(socket.gethostname())

        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue
        
            self.stdout.write('%s\n' % path)
            try:
                ret = yield self._daddb.getTrackByHostPath(hostname, path)
            except error.Error, e:
                if e.status == 404:
                    self.stderr.write('Database or view does not exist.\n')
                    reactor.stop()
                    defer.returnValue(3)
                    return

            ret = list(ret)
            if len(ret) == 0:
                self.stdout.write('Not in database.\n')
            else:
                self.stdout.write('In database in %d tracks.\n' % len(ret))
