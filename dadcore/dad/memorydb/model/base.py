# -*- Mode: Python; test-case-name: dad.test.test_memorydb_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.model import scorable


class MemoryModel(scorable.BackedModel):
    """
    I am a base class for models backed by a memory database.
    """

    def get(self, subjectId):
        return

class ScorableMemoryModel(MemoryModel):
    """
    I am a base class for models backed by a memory database.

    @type scores: list of L{Score}
    """
    scores = None


    def __init__(self, memorydb):
        scorable.BackedModel.__init__(self, memorydb)
        self.scores = []

    def get(self, subjectId):
        return

    def getScores(self, userName=None):
        return [s for s in self.scores if not userName or s.user == userName]

    def setScore(self, userName, categoryName, score):
        return self.database.setScore(self, userName, categoryName, score)

    def score(self, userName, categoryName, score):
        return self.database.score(self, userName, categoryName, score)
