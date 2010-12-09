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
import optparse
import pickle

from dad.extern.log import log

_DEFAULT_LOOPS = -1
_DEFAULT_RANDOM = True

_DEFAULT_TRACKS = 'tracks.pickle'

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


class OptionParser(optparse.OptionParser):
    standard_option_list = [
        optparse.Option('-l', '--loops',
            action="store", dest="loops", type="int",
            help="how many times to loop the playlist (defaults to %default)",
            default=_DEFAULT_LOOPS),
        optparse.Option('-r', '--random',
            action="store_true", dest="random",
            help="play tracks in random order (defaults to %default)",
            default=_DEFAULT_RANDOM),
    ]



class Selecter(log.Loggable):
    """
    I implement a selection strategy.
    """
    option_parser_class = OptionParser

    def setup(self):
        """
        Override me to set up the selecter, connect to the backend, and prime
        the first few selected tracks.

        Should get at least two tracks so playback can begin and get can be
        called.

        Should get more tracks in the background.

        Can return a deferred which will be waited on.
        """
        raise NotImplementedError

    def get(self):
        """
        Get a track to play.

        @rtype: tuple of (str, L{TrackMix})
        """
        raise NotImplementedError

class SimplePlaylistOptionParser(OptionParser):
    standard_option_list = OptionParser.standard_option_list + [
        optparse.Option('-t', '--tracks',
            action="store", dest="tracks",
            help="A tracks pickle to read trackmix data from (default '%s'" %
                _DEFAULT_TRACKS,
            default=_DEFAULT_TRACKS),
        optparse.Option('-p', '--playlist',
            action="store", dest="playlist",
            help="A playlist file to play tracks from"),
    ]


class SimplePlaylistSelecter(Selecter):
    """
    I simply select tracks from a tracks pickle and playlist, linear or random.

    Each track gets played once.  When all tracks are played, the process
    is repeated.

    @param tracks: dict of path -> list of trackmix
    @type  tracks: dict of str -> list of L{dad.audio.mixing.TrackMix}
    """

    option_parser_class = SimplePlaylistOptionParser

    def __init__(self, options):
        self._tracks = pickle.load(open(options.tracks))

        self._playlist = options.playlist
        self._random = options.random
        self._loop = 0
        self._loops = options.loops
        self.debug('Creating selecter, for %d loops', self._loops)

        self._selected = [] # list of tuple of (path, trackMix)

    def setup(self):
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


