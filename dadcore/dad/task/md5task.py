# -*- Mode: Python; test-case-name: dad.task.md5 -*-
# vi:si:et:sw=4:sts=4:ts=4

# DAD - Digital Audio Database

# Copyright (C) 2011 Thomas Vander Stichele

# This file is part of DAD.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

from dad.extern.log import log
from dad.extern.task import task


import md5

from zope import interface

from twisted.internet import interfaces
from twisted.protocols import basic

class MD5Consumer:
    interface.implements(interfaces.IConsumer)

    def __init__(self, task):
        self._md5 = md5.md5()
        self._producer = None
        self._task = task

    def registerProducer(self, producer, streaming):
        self._producer = producer
        producer.resumeProducing()

    def unregisterProducer(self):
        self._producer = None
        self.md5sum = self._md5.hexdigest()

    def write(self, data):
        self._md5.update(data)
        # avoid maximum recursion depth
        self._task.schedule(0, self._producer.resumeProducing)


class MD5Task(log.Loggable, task.Task):
    """
    I calculate an md5sum.

    @ivar md5sum: the resulting md5sum
    """

    md5sum = None
    description = 'Calculating TRM fingerprint'

    def __init__(self, path):
        assert type(path) is unicode, "path %r is not unicode" % path

        self._path = path
        self._md5sum = None

        self._sender = basic.FileSender()
        self._consumer = MD5Consumer(self)

        self._handle = open(path, 'r')

    def start(self, runner):
        task.Task.start(self, runner)

        d = self._sender.beginFileTransfer(self._handle, self._consumer)
        def cb(_):
            self.md5sum = self._consumer.md5sum
            self.stop()
        d.addCallback(cb)
