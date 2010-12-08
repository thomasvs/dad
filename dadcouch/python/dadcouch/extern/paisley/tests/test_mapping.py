# -*- Mode: Python; test-case-name: paisley.tests.test_mapping -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2008
# See LICENSE for details.

"""
Tests for the object mapping API.
"""

from twisted.trial.unittest import TestCase

from paisley import mapping, views

from paisley.tests import stub

# an object for a view result that includes docs
class Tag(mapping.Document):
    name = mapping.TextField()
    siblings = mapping.ListField(mapping.TextField)

class MappingTests(TestCase):
    def setUp(self):
        self.fc = stub.TagStubCouch()

    def test_queryView(self):
        """
        Test that querying a view gives us an iterable of our user defined
        objects.
        """
        v = views.View(self.fc, None, None, 'all_tags', Tag,
            include_docs=True)

        def _checkResults(results):
            results = list(results)
            self.assertEquals(len(results), 3)

            # this used to be not executed because it worked on the empty
            # generator; so guard against that
            looped = False
            for tag in results:
                looped = True
                self.assertIn(tag.name, ['foo', 'bar', 'baz'])
                self.assertIn(tag.siblings[0], ['larry', 'curly', 'moe'])
            self.failUnless(looped)

        d = v.queryView()
        d.addCallback(_checkResults)
        return d

# specific type tests
class TestDoc(mapping.Document):
    dictField = mapping.DictField(mapping.Mapping.build(
        name=mapping.TextField(), email=mapping.TextField()))

    tupleField = mapping.TupleField((mapping.LongField, mapping.FloatField))

    listTupleField = mapping.ListField(
        mapping.TupleField((mapping.LongField, mapping.FloatField)))

class MappingTypeTests(TestCase):
    def testDictField(self):
        doc = TestDoc(dictField={
            'name': 'John Doe',
            'email': 'john@doe.com'
        })
        self.assertEquals(doc.dictField['name'], 'John Doe')

    def testTupleField(self):
        doc = TestDoc(tupleField=(0L, 1.0))
        self.assertEquals(doc.tupleField[0], 0L)
        self.assertEquals(type(doc.tupleField[0]), long)
        self.assertEquals(type(doc.tupleField[1]), float)

    def testListTupleField(self):
        doc = TestDoc(listTupleField=[
            (0L, 1.0),
            (1L, 2.0)
        ])
        self.assertEquals(doc.listTupleField[0][0], 0L)
        self.assertEquals(type(doc.listTupleField[0][0]), long)
        self.assertEquals(type(doc.listTupleField[0][1]), float)

