# -*- Mode: Python; test-case-name: dad.test.test_common_selecter -*-
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

def getPathArtist(path):
    import re
    regexps = [
        re.compile(r"""
            (?P<track>\d+).
            (?P<artist>[^-]*) - 
            (?P<title>.*)""", re.VERBOSE),
        re.compile(r"""
            (?P<artist>[^-]*)\s*- 
            (?P<title>.*)""", re.VERBOSE),
    ]

    # get artist from a file path
    basename = os.path.basename(path)

    for regexp in regexps:
        m = regexp.search(basename)
        if m:
            # FIXME: our regexps don't drop the spaces right
            return m.group('artist').strip()

class Selecter(log.Loggable):
    """
    I implement a selection strategy.
    """

class SimplePlaylistSelecter(Selecter):
    """
    I simply select tracks from a tracks pickle and playlist, linear or random.

    Each track gets played once.  When all tracks are played, the process
    is repeated.

    @param tracks: dict of path -> list of trackmix
    @type  tracks: dict of str -> list of L{dad.audio.mixing.TrackMix}
    """
    def __init__(self, tracks, playlist=None, random=False, loops=-1):
        self.debug('Creating selecter, for %d loops', loops)
        self._tracks = tracks
        self._playlist = playlist
        self._random = random
        self._loop = 0
        self._loops = loops

        self._selected = [] # list of tuple of (path, trackMix)
        self._load()

    def shuffle(self, files):
        """
        Override me for different shuffling algorithm.
        """
        res = files[:]
        random.shuffle(res)
        return res

    def _load(self):
        self.debug('%d tracks in pickle', len(self._tracks))
        files = self._tracks.keys()
        if self._playlist:
            files = open(self._playlist).readlines()

        self.debug('%d files', len(files))
        if self._random:
            self.debug('shuffling')
            # this can repeat tracks
            paths = self.shuffle(files)
        else:
            paths = files[:]
        # we pop tracks from the top, so reverse the paths we go through
        paths.reverse()
        for path in paths:
            path = path.strip()
            try:
                # FIXME: pick random track in file
                # for now, pick first one
                self._selected.append((path, self._tracks[path][-1]))
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
            self.debug('get out of selected tracks, %d/%d loops',
                self._loop, self._loops)
            if self._loop == self._loops:
                return None

            self._load()
            self._loop += 1

        tuple = self._selected[-1]
        del self._selected[-1]

        return tuple

    def select(self):
        t = self.get()
        self.info('selecter: selected %r', t)
        return t

class SpreadingArtistSelecter(SimplePlaylistSelecter):
    """
    I shuffle tracks by spreading the same artists throughout the playlist.
    """
    # FIXME: not taking tracks in the file into account
    def shuffle(self, paths):
        result = []

        artists = {}

        for path in paths:
            artist = getPathArtist(path)
            if not artist in artists.keys():
                artists[artist] = []
            artists[artist].append(path)

        print artists

        return paths

if __name__ == '__main__':
    print 'selecting'
    path = sys.argv[1]
    paths = open(path).readlines()
    selecter = SpreadingArtistSelecter()


