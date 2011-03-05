#!/usr/bin/python

# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# DAD - Digital Audio Database
# Copyright (C) 2008 Thomas Vander Stichele <thomas at apestaart dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import os
import optparse

from twisted.internet import reactor, protocol, base, stdio
from twisted.spread import pb
from twisted.cred import portal

from zope.interface import implements

try:
    from dad.common import log
except:
    class Log:
        def init(self):
            pass

        def debug(self, cat, f, *args):
            if args:
                print "%s: %s" % (cat, f % args)
            else:
                print "%s: %s" % (cat, f)
    log = Log()

### server code
class MasterHeaven(pb.Root):
    logCategory = 'master-heaven'

    implements(portal.IRealm)

    def remote_echo(self, st):
        log.debug('master', 'echoing: %r', st)
        return st

    ### portal.IRealm method

    def requestAvatar(self, avatarId, mind, *interfaces):
        if pb.IPerspective in interfaces:
            avatar = self.avatarClass(self, avatarId, mind)
            assert avatarId not in self.avatars
            self.avatars[avatarId] = avatar
            return pb.IPerspective, avatar, avatar.logout
        else:
            raise NotImplementedError("no interface")

    def removeAvatar(self, avatarId):
        if avatarId in self.avatars:
            del self.avatars[avatarId]
        else:
            self.warning("some programmer is telling me about an avatar "
                         "I have no idea about: %s", avatarId)


# FIXME: rename
# FIXME: why do I need this fake stub class ? Is there no more direct way
# ti hook to writeToChild
class MyTransport:
    def __init__(self, protocol, childWriteFd):
        self._protocol = protocol
        self._childWriteFd = childWriteFd

    def write(self, value):
        # print 'THOMAS: MyTransport: write %r on %r', value, self._protocol
        # this is the glue that lets the server send the pb dialects initially
        self._protocol.writeToChild(self._childWriteFd, value)

class SlaveProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, server, childWriteFd):
        self._server = server
        self._childWriteFd = childWriteFd

    def setTransport(self, transport):
        log.debug('spp', 'THOMAS: SPP: setTransport %r', transport)
        self.transport = transport

    def connectionMade(self):
        log.debug('slavepp', 'connectionMade')
        protocol = self._server.buildProtocol(None)
        protocol.transport = MyTransport(self.transport, self._childWriteFd)
        # FIXME: need to get a transport in here, like Broker
        log.debug('slavepp', 'protocol %r, transport %r',
            protocol, protocol.transport)
        self._protocol = protocol
        protocol.connectionMade()

    def childDataReceived(self, childFD, data):
        log.debug('slavepp', 'childDataReceived on fd %r, data %r',
            childFD, data)
        self._protocol.dataReceived(data)

    def processEnded(self, status):
        log.debug('slavepp', 'processEnded')
        rc = status.value.exitCode
        if rc == 0:
            self.deferred.callback(self)
        else:
            self.deferred.errback(rc)

# FIXME: rewrite to listenFD/listenStdio
def spawnSlave():
    log.debug('master', 'spawning slave')
    server = pb.PBServerFactory(MasterHeaven())

    # we'll use fd3 for reading from child, and fd4 for writing to it
    mypp = SlaveProcessProtocol(server, 4)
    childFDs = {0: 0, 1: 1, 2: 2, 3: 'r', 4: 'w'}
    transport = reactor.spawnProcess(mypp, sys.argv[0],
                args=[sys.argv[0], '--slave'],
                     env=os.environ, childFDs=childFDs)
    mypp.setTransport(transport)

### client code
class MyStandardIO(stdio.StandardIO):
    def failIfNotConnected(self, exception):
        log.debug('slave', 'THOMAS: failIfNotConnected: %r', exception)

# compare to tcp.Connector
class ProcessClientConnector(base.BaseConnector):
    def _makeTransport(self):
        log.debug('slave', 'THOMAS: makeTransport: %r', self.state)
        # protocol = self.factory.buildProtocol(None) # FIXME: addr

        # FIXME: makeTransport is called before setting timeoutID;
        # buildProtocol thus resets it to soon for us 
        protocol = self.buildProtocol(None) # FIXME: addr
        log.debug('slave', 'timeoutID %r', self.timeoutID)
        log.debug('slave', 'THOMAS: protocol %r', protocol)
        t = MyStandardIO(protocol, stdin=4, stdout=3)
        # FIXME: writing works to get it to the server, but how does the
        # chitchat really start ?
        # t.write('kakapipi')
        # t.startReading()
        log.debug('slave', 'host: %r, peer: %r', t.getHost(), t.getPeer())
        return t

# modeled on connectTCP
def connectStdio(factory):
    TIMEOUT = 3
    c = ProcessClientConnector(factory, TIMEOUT, reactor)
    log.debug('slave', 'before connecting: %r', c.state)
    c.connect()
    log.debug('slave', 'after connecting: state %r, timeoutid %r, transport %r',
        c.state, c.timeoutID, c.transport)
    return c

def slave():
    # this is the slave
    log.debug('slave', 'slave is started')

    # log in to manager with a pb client over the processprotocol somehow
    clientFactory = pb.PBClientFactory()
    c = connectStdio(clientFactory)
    # FIXME: we shouldn't do this manually
    c.cancelTimeout()


    log.debug('slave', 'clientFactory._broker %r', clientFactory._broker)
    d = clientFactory.getRootObject()
    # import code; code.interact(local=locals())
    def cb(root):
        log.debug('slave', 'slave got root: %r' % root)
        return root.callRemote("echo", "hello network")

    d.addCallback(cb)

def main():
    log.init()

    parser = optparse.OptionParser()

    parser.add_option('-s', '--slave',
        action="store_true", dest="slave",
        help="start as a slave to the daemon")

    options, args = parser.parse_args(sys.argv[1:])

    print 'running reactor'

    if not options.slave:
        reactor.callLater(0, spawnSlave)
    else:
        reactor.callLater(0, slave)

    reactor.run()

main()
