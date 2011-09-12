# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
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

    def getScores(self):
        return self.scores

    def setScore(self, subject, userName, categoryName, score):
        found = False

        for i, s in enumerate(self.scores):
            if s.user == userName and s.category == categoryName:
                self.scores[i].score = score
                found = True

        if not found:
            s = data.Score()
            s.subject = self
            s.user = userName
            s.category = categoryName
            s.score = score
            self.scores.append(s)

        return self
