# -*- Mode: Python; test-case-name: dad.test.test_common_iterators -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# DAD - Digital Audio Database
# Copyright (C) 2008 Thomas Vander Stichele <thomas at apestaart dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import unittest

from dad.common import iterators

class TMergeTest(unittest.TestCase):
    def testTMerge(self):
        i1 = (i for i in [0, 1, 2])
        i2 = (i for i in ['a', 'b'])

        l = list(iterators.tmerge(i1, i2))
        self.assertEquals(l, [0, 'a', 1, 'b', 2])
