# -*- Mode: Python; test-case-name: dad.test.test_memorydb_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base
from dad.base import data


class MemoryModel(base.Model):
    """
    I am a base class for models backed by a memory database.
    """

    def __init__(self, memorydb):
        self._db = memorydb

    def get(self, subjectId):
        return

class ScorableMemoryModel(MemoryModel):
    """
    I am a base class for models backed by a memory database.

    @type scores: list of L{Score}
    """
    scores = None


    def __init__(self, memorydb):
        MemoryModel.__init__(self, memorydb)
        self.scores = []

    def get(self, subjectId):
        return

    def getScores(self, userName=None):
        return [s for s in self.scores if not userName or s.user == userName]

    def setScore(self, userName, categoryName, score):
        return self._db.setScore(self, userName, categoryName, score)

    def score(self, userName, categoryName, score):
        return self._db.score(self, userName, categoryName, score)
