# -*- Mode: Python -*-
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

import gc
import unittest

class GarbageTracker(object):
    """
    I track specific object types tracked by the garbage collector.
    Subclass me to find where your Python code leaks these objects.

    @cvar trackedTypes: the object types you want to track.
    """

    trackedTypes = []

    _tracked = {}

    def collectGarbage(self):
        """
        Run the garbage collector until no new objects are collected.
        Return the number of garbage-collected objects.

        @rtype: int
        """
        ret = 0

        while True:
            collected = gc.collect()
            ret += collected
            if collected == 0:
                break

        return ret

    def trackGarbage(self):
        """
        Initialize tracking of garbage collection for all types in
        garbageTypes.
        """
        self.cleanTracked()
        self.collectGarbage()

        for c in self.trackedTypes:
            self._tracked[c] = [
                o for o in gc.get_objects() if isinstance(o, c)]

    def cleanTracked(self):
        """
        Clean the list of tracked objects.
        """

        del self._tracked
        self._tracked = {}

    def getNewTracked(self):
        """
        Get a list of all newly tracked objects since the last call to
        trackGarbage.

        @rtype: list of object
        """

        new = []

        for c in self.trackedTypes:
            objs = [o for o in gc.get_objects() if isinstance(o, c)]
            new.extend([o for o in objs if o not in self._tracked[c]])

        return new

class GarbageTrackerTest(unittest.TestCase, GarbageTracker):
    """
    Subclass me for tests with automatic garbage tracking.
    Will fail if during tearDown any new garbage is left.
    """

    def setUp(self):
        self.trackGarbage()

    def tearDown(self):
        new = self.getNewTracked()
        self.failIf(new, new)
