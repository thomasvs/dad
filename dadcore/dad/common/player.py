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

import os
import sys
import time

from twisted.internet import defer

from dad.extern.log import log

class Player(log.Loggable):
    """
    I implement playback of scheduled tracks.
    """
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.scheduler.connect('scheduled', self.scheduled_cb)

    ### base method implementations

    ### overridable methods
    def setup(self):
        raise NotImplementedError


    def start(self):
        raise NotImplementedError

    def scheduled_cb(self, scheduler, scheduled):
        raise NotImplementedError

class FakePlayer(Player):
    """
    I am a player that doesn't actually play back, only lets time pass
    and notifies of position.
    """

    SPEED = 1.0
    QUEUE_SIZE = 60 * 30 # 30 mins

    def _scheduleUntilCb(result):
        pass
        
    def setup(self):
        # Fill up minimal queue size
        d = self.scheduler.schedule()
        return d

    def start(self):
        self._started = time.now()

    def scheduled_cb(self, scheduler, scheduled):
        print 'THOMAS: scheduled_cb', scheduled


