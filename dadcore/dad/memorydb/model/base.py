# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base


class MemoryModel(base.Model):
    """
    I am a base class for models backed by a memory database.
    """

    def __init__(self, memorydb):
        self._db = memorydb

    def get(self, subjectId):
        return
