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
import math
import random

from dad.extern.log import log

class Selecter(log.Loggable):
    """
    I implement a selection strategy.
    """

class SimplePlaylistSelecter(Selecter):
    """
    I simply select tracks from a tracks pickle and playlist, linear or random.
    """
    def __init__(self, tracks, playlist=None, random=False):
        self._tracks = tracks
        self._playlist = playlist
        self._random = random

        self._selected = [] # list of tuple of (path, trackMix)

    def _load(self):
        files = self._tracks.keys()
        if self._playlist:
            files = open(self._.playlist).readlines()

        if self._random:
            # this can repeat tracks
            paths = [random.choice(files) for i in range(len(files))]
        else:
            paths = files[:]
        # we pop tracks from the top, so reverse the paths we go through
        paths.reverse()
        for path in paths:
            path = path.strip()
            try:
                # FIXME: pick random track in file
                self._selected.append((path, self._tracks[path][0]))
            except KeyError:
                print "%s not in pickle, skipping" % path
            except IndexError:
                print "path %s does not have trackmix object in pickle" % path
        
    def get(self):
        """
        Get a track to play.

        @rtype: tuple of (str, L{TrackMix})
        """
        if not self._selected:
            self._load()

        tuple = self._selected[-1]
        del self._selected[-1]

        return tuple
