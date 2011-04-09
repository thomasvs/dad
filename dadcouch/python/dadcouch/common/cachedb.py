# -*- Mode: Python; test-case-name: paisley.tests.test_couchdb -*-
# vi:si:et:sw=4:sts=4:ts=4

# Copyright (c) 2007-2008
# See LICENSE for details.

"""
CouchDB caching client.
"""

from twisted.internet import defer

from dadcouch.extern.paisley import client

class CachingCouchDB(client.CouchDB):
    """
    I cache parsed docs.
    """

    def __init__(self, host, port=5984, dbName=None,
                       username=None, password=None):
        client.CouchDB.__init__(self, host, port, dbName, username, password)
        self._cache = {} # dict of dbName to dict of id to doc

        self.lookups = 0
        self.hits = 0
        self.cached = 0

    def mapped(self, dbName, objId, obj):
        if not dbName in self._cache.keys():
            self._cache[dbName] = {}

        if not self._cache[dbName].has_key(objId):
            self._cache[dbName][objId] = obj
            self.cached += 1
    
    def map(self, dbName, objId, objFactory):
        self.lookups += 1

        # return cached version if in cache
        if objId in self._cache[dbName].keys():
            self.hits += 1
            return defer.succeed(self._cache[dbName][objId])

        # otherwise, load and map through parent implementation
        return client.CouchDB.map(self, dbName, objId, objFactory)

    def getCached(self, dbName, objId):
        return self._cache[dbName][objId]
