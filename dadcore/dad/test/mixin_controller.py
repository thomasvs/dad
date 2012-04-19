# -*- Mode: Python; test-case-name: dad.test.test_controller -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.base import base
from dad.controller import artist as cartist
from dad.common import log
from dad.logic import database

"""
Base class for tests for controller implementations.
"""

class FakeArtistView(base.View):

    scored = False

    def connect(self, event, callback):
        self.debug('FakeArtistView: scoring')
        self._callback = callback
        self._callback(self, u'Good', 0.9)
        self.scored = True
        self.debug('FakeArtistView: scored')


class BaseTestCase(log.Loggable):
    """
    Subclass me to have database-specific tests run against the generic
    tests.

    The subclass is responsible for setting the testdb instance variable.

    @ivar testdb:   the database being tested
    @type testdb:   an implementer of L{idad.IDatabase}
    @ivar provider: the database provider
    @type provider: an implementor of L{idad.IDatabaseProvider}
    """

    @defer.inlineCallbacks
    def addFirstTrack(self):
        """
        @rtype: mappings.Track
        """
        # add a first track
        # FIXME: no name makes sense or not?
        tm = self.testdb.newTrack(name=None)
        yield self.testdb.save(tm)

        info = database.FileInfo('localhost', '/tmp/first.flac')
        metadata = database.TrackMetadata()
        metadata.title = u'Milez iz Ded'
        metadata.artist = u'The Afghan Whigs'

        tm.addFragment(info, metadata=metadata)
        ret = yield self.testdb.save(tm)
        defer.returnValue(ret)

class ArtistControllerTestCase(BaseTestCase):

    @defer.inlineCallbacks
    def testArtist(self):
        from twisted.internet import reactor

        aModel = self.testdb.new('artist', name=u'The Afghan Whigs')
        aController = cartist.ArtistController(aModel)
        aView = FakeArtistView()
        aController.addView(aView)

        self.failUnless(aView.scored)

        # FIXME: wait for notification ?
        # the doc is not saved yet; happens next time deferred generator
        # runs, but our next call already launches getting scores before
        # doc is saved
        # so do a defer/yield trick to pass time
        d = defer.Deferred()
        reactor.callLater(0.1, d.callback, None)
        yield d

        scores = yield aModel.getScores()
        self.assertEquals(len(scores), 1)
        score = scores[0]
        self.assertEquals(score.category, u'Good')
        self.assertEquals(score.score, 0.9)

# FIXME: factor out method
def makeTestCaseClasses(cls):
        """
        Create a L{TestCase} subclass which mixes in C{cls} for each known
        test case.

        @param cls: the base class for the database-specific handling
                    including a setUp that sets testdb and provider ivars.
        """
        classes = {}
        for klazz in [
            ArtistControllerTestCase,
            ]:
            name = klazz.__name__
            class testcase(cls, klazz):
                __module__ = cls.__module__

                @defer.inlineCallbacks
                def setUp(self):
                    if hasattr(cls, 'setUp'):
                        yield cls.setUp(self)

                    if hasattr(self._klazz, 'setUp'):
                        yield self._klazz.setUp(self)

            testcase.__name__ = name
            # we can't use klazz directly in setUp, since when it's evaluated
            # it's set to the last class in the loop
            testcase._klazz = klazz
            classes[testcase.__name__] = testcase
        return classes
