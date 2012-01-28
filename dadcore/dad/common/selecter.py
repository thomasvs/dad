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
import random
import optparse
import pickle

from twisted.internet import defer

from dad.common import pathscan

from dad.extern.log import log

_DEFAULT_LOOPS = -1
_DEFAULT_RANDOM = True

# _DEFAULT_TRACKS = 'tracks.pickle'


class Selected(object):
    """
    I represent a selected object.
    """
    path = None
    trackmix = None

    artists = None
    title = None

    def __init__(self, path, trackmix, artists=None, title=None):
        self.path = path
        self.trackmix = trackmix
        self.artists = artists or []
        self.title = title

class OptionParser(optparse.OptionParser):
    standard_option_list = [
        optparse.Option('-l', '--loops',
            action="store", dest="loops", type="int",
            help="how many times to loop the playlist (defaults to %default)",
            default=_DEFAULT_LOOPS),
        optparse.Option('-R', '--no-random',
            action="store_false", dest="random",
            help="do not play tracks in random order (defaults to %default)",
            default=_DEFAULT_RANDOM),
    ]



class Selecter(log.Loggable):
    """
    I implement a selection strategy.
    """
    logCategory = 'selecter'

    option_parser_class = OptionParser

    # loadDeferred should return a count of tracks loaded
    loadDeferred = None # set when a complete load is in progress in backend


    def __init__(self, options):
        self._selected = [] # list of Selected objects

        if not options:
            parser = self.option_parser_class()
            options, _ = parser.parse_args([])
        self.options = options


    ### base method implementations

    def get(self):
        """
        Get a track to play, possibly waiting to (re)query the backend.

        @rtype: deferred firing tuple of (str, L{TrackMix}) or None when done.
        """
        # if we still have tracks loaded, return them
        res = self.getNow()

        if res:
            self.debug('get(): returning immediately %r', res)
            return defer.succeed(res)

        # no tracks loaded, so if necessary reload
        if self.loadDeferred:
            self.debug('get(): already loading, returning a deferred for later')
            d = defer.Deferred()
            # wait for results to come in

            def loadCb(_):
                self.debug('get(): loaded, returning a recursive get')
                # recursively get
                d2 = self.get()
                d2.addCallback(lambda r: d.callback(r))
                return d2
            self.loadDeferred.addCallback(loadCb)

            return d

        # reload 
        self.debug('get(): ran out of selected tracks, %d/%d loops',
            self._loop, self._loops)
        if self._loop == self._loops:
            # done
            self.debug('get(): completed all loops')
            return defer.succeed(None)

        self.debug('get(): reloading')
        d = self.load()

        def loadCb(result):
            self._loop += 1
            if result is None:
                self.warning('get(): no tracks match')
                raise IndexError('no tracks match')
                return

            self.debug('get(): loaded, starting loop %d of %d',
                self._loop, self._loops)
        d.addCallback(loadCb)
        # another recursive call
        d.addCallback(lambda _: self.get())

        return d

    def getNow(self):
        """
        Get a track to play, or return False if none are ready to be selected.

        @rtype: tuple of (str, L{TrackMix})
        """
        if not self._selected:
            return None

        tuple = self._selected[0]
        del self._selected[0]

        return tuple

    def select(self):
        """
        @rtype: L{Selected}
        """
        d = self.get()

        def _getCb(result):
            self.info('selected %r', result)
            if not os.path.exists(result.path):
                self.warning('path %r does not exist', result.path)
                print 'WARNING: path %r does not exist' % result.path
            return result
        d.addCallback(_getCb)

        return d

    def selectNow(self):
        t = self.getNow()
        if t:
            self.info('selected %r', t)
        else:
            self.info('could not select a track now')
        return t

    def selected(self, selected):
        assert isinstance(selected, Selected)
        self._selected.append(selected)

    ### overridable methods
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

    def load(self):
        """
        Load all tracks to be scheduled.

        @returns: a deferred firing True if tracks could be loaded.
        @rtype:   L{defer.Deferred} firing bool
        """
        raise NotImplementedError


class SimplePlaylistOptionParser(OptionParser):
    standard_option_list = OptionParser.standard_option_list + [
        optparse.Option('-t', '--tracks',
            action="store", dest="tracks",
            help="A tracks pickle to read trackmix data from"),
        optparse.Option('-p', '--playlist',
            action="store", dest="playlist",
            help="A playlist file to play tracks from"),
    ]


class SimplePlaylistSelecter(Selecter):
    """
    I simply select tracks from a tracks pickle and playlist, linear or random.

    Each track gets played once.  When all tracks are played, the process
    is repeated.

    @ivar  _tracks: dict of path -> list of trackmix
    @type  _tracks: dict of str -> list of L{dad.audio.mixing.TrackMix}
    """

    option_parser_class = SimplePlaylistOptionParser

    def __init__(self, options):
        Selecter.__init__(self, options)

        self._tracks = {}
        if self.options.tracks:
            self._tracks = pickle.load(open(self.options.tracks))
            if len(self._tracks) == 0:
                raise IndexError("The tracks pickle %s is empty" %
                    self.options.tracks)

        self._playlist = self.options.playlist
        self._random = self.options.random
        self._loop = 0
        self._loops = self.options.loops
        self.debug('Creating selecter, for %d loops', self._loops)
        self.debug('Random: %r', self._random)

        self._selectables = [] # list of Selected
 
    def setup(self):
        # this loads all synchronously, but should be fast
        self._load()
        return defer.succeed(None)

    def load(self):
        res = self._load()
        return defer.succeed(res)

    # FIXME: should this be pushed to base class ?
    def shuffle(self, files):
        """
        Override me for different shuffling algorithm.
        """
        res = files[:]
        random.shuffle(res)
        return res

    def _load(self):
        self.debug('%d tracks in pickle', len(self._tracks))
        if len(self._tracks) == 0:
            raise IndexError("The tracks pickle is empty")
        files = self._tracks.keys()
        if self._playlist:
            files = open(self._playlist).readlines()
            files = [line for line in files if not line.startswith('#')]

        self.debug('%d files', len(files))
        for path in files:
            if not path.startswith(os.path.sep) and self._playlist:
                path = os.path.join(os.path.dirname(self._playlist), path)
            path = path.strip()
            # FIXME: checking the file is expensive
            # if not os.path.exists(path):
            #    print "%s does not exist, skipping" % path
            #    continue
            try:
                trackmix = self._tracks[path][-1]
            except KeyError:
                print "%s not in pickle, skipping" % path
                continue
            except IndexError:
                print "path %s does not have trackmix object in pickle" % path
                continue

            artists, title = pathscan.parsePath(path) # FIXME: split
            if not artists and not title:
                # fall back to file name for title
                title = os.path.basename(os.path.splitext(path)[0])
            s = Selected(path, trackmix, artists=artists, title=title)
            self._selectables.append(s)

        if self._random:
            self.debug('shuffling')
            # this can repeat tracks
            selectables = self.shuffle(self._selectables)
        else:
            selectables = self._selectables[:]
        # we pop tracks from the top, so reverse the paths we go through
        selectables.reverse()
        for selectable in selectables:
            self.selected(selectable)
        
        return True

class SpreadingArtistSelecter(SimplePlaylistSelecter):
    """
    I shuffle tracks by spreading the same artists throughout the playlist.
    """
    # FIXME: not taking tracks in the file into account
    def shuffle(self, paths):
        result = []

        artists = {}

        # FIXME: reuse selectables logic
        for path in paths:
            artist = pathscan.getPathArtist(path)
            if not artist in artists.keys():
                artists[artist] = []
            artists[artist].append(path)

        paths = []

        for artist, p in artists.items():
            paths.append(random.choice(p))

        res = paths[:]

        if self._random:
            random.shuffle(res)

        return res


if __name__ == '__main__':
    from twisted.internet import reactor
    log.init('DAD_DEBUG')

    parser = SpreadingArtistSelecter.option_parser_class()
    opts, args = parser.parse_args(sys.argv[1:])

    selecter = SpreadingArtistSelecter(opts)

    state = {
        'count': 0,
        'deferred': defer.Deferred(), # fire when we're done
    }

    def selectedCb(selected, state):
        state['count'] += 1
        print "selected: %3d: %r" % (state['count'], selected)
        if state['count'] == 100:
            state['deferred'].callback(None)
            return

        # callLater to avoid recursion of deferreds
        def callLater(state):
            d = selecter.select()
            d.addCallback(selectedCb, state)
            return d

        reactor.callLater(0L, callLater, state)

    d = selecter.setup()
    def setupCb(_):
        d = selecter.select()
        d.addCallback(selectedCb, state)
        return state['deferred']
    d.addCallback(setupCb)


    # finish
    d.addCallback(lambda _: reactor.callLater(0L, reactor.stop))

    reactor.run()
