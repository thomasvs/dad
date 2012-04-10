# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
A helper class for Twisted commands.
"""

from dad.extern.log import log

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
            try:
                d = self.doLater(args)
            except Exception, e:
                self.warning('Exception during doLater: %r',
                    log.getExceptionMessage(e))
                self.reactor.stop()
                return 3

            d.addCallback(lambda _: self.reactor.stop())
            d.addErrback(log.warningFailure, swallow=False)
            def eb(failure):
                self.stderr.write('Failure: %s\n' %
                    log.getFailureMessage(failure))
                self.reactor.stop()
            d.addErrback(eb)

        self.reactor.callLater(0, later)

        self.reactor.run()

    def doLater(self):
        raise NotImplementedError
