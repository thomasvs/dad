# -*- Mode: Python; test-case-name: paisley.tests.test_views -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2008
# See LICENSE for details.

"""
Tests for the object mapping view API.
"""

from twisted.trial.unittest import TestCase

from paisley.views import View

from paisley.tests import stub


# an object for a view result not including docs
class TagViewRow(object):
    def fromDict(self, dictionary):
        self.name = dictionary['key']
        self.count = dictionary['value']


class ViewTests(TestCase):
    def setUp(self):
        self.fc = stub.TagStubCouch()

    def test_queryView(self):
        """
        Test that querying a view gives us an iterable of our user defined
        objects.
        """
        v = View(self.fc, None, None, 'all_tags', TagViewRow)

        def _checkResults(results):
            results = list(results)
            self.assertEquals(len(results), 3)

            # this used to be not executed because it worked on the empty
            # generator; so guard against that
            looped = False
            for tag in results:
                looped = True
                self.assertIn({'key': tag.name, 'value': tag.count},
                              self.fc._views['all_tags']['rows'])
            self.failUnless(looped)

        d = v.queryView()
        d.addCallback(_checkResults)
        return d
