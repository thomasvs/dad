# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
A helper class for Twisted commands.
"""


from dad.common import logcommand


# FIXME: move this to the command module
class TwistedCommand(logcommand.LogCommand):

    def installReactor(self):
        """
        Override me to install your own reactor.
        """
        from twisted.internet import reactor
        self.reactor = reactor

    def do(self, args):
        self.installReactor()


        def later():
            d = self.doLater(args)
            d.addCallback(lambda _: self.reactor.stop())

        self.reactor.callLater(0, later)

        self.reactor.run()

    def doLater(self):
        raise NotImplementedError
