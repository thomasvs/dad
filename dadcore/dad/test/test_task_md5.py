# -*- Mode: Python; test-case-name: dad.test.test_task_md5 -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import commands
import tempfile

import unittest

from dad.extern.task import task

from dad.task import md5task


class MD5Test(unittest.TestCase):
    def setUp(self):
        self.runner = task.SyncRunner(verbose=False)

    def testMD5(self):
        fd, path = tempfile.mkstemp(suffix=u'dad.test.md5')
        os.write(fd, '0xdeadbeef')
        os.close(fd)
        output = commands.getoutput('md5sum %s' % path)
        md5sum = output.split()[0]

        task = md5task.MD5Task(path)
        self.runner.run(task)

        self.assertEquals(task.md5sum, md5sum)
        os.unlink(path)
