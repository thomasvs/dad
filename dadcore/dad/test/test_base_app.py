# -*- Mode: Python; test-case-name: dad.test.test_base_app -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest

from dad.base import app
from dad.models import app as mapp
from dad.memorydb import memory

class AppControllerTest(unittest.TestCase):

    def setUp(self):
        db = memory.MemoryDB()
        self._am = mapp.MemoryAppModel(db)
        self._ac = app.AppController(self._am)

    def test_getTriad(self):
        controller, model, views = self._ac.getTriad('ArtistSelector')
