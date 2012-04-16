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
import getpass
import socket

from twisted.internet import defer
from twisted.python import reflect

from dad.common import pathscan

from dad.extern.log import log


def getSelecter(spec, stdout=None, database=None):
    """
    Parse a specification of a selecter to an actual selecter instance.

    @param spec:   a spec to parse
    @param stdout: a file object to output help to if needed

    @rtype: L{Selecter}
    """
    selecterArgs = []
    selecterClassName = spec

    if ':' in spec:
        selecterClassName, line = spec.split(':', 1)
        selecterArgs = line.split(':')
    selecterClass = reflect.namedAny(selecterClassName)
    parser = selecterClass.option_parser_class()
    log.debug('getSelecter', 'Creating selecter %r with args %r',
        selecterClass, selecterArgs)

    if 'help' in selecterArgs:
        if stdout:
            stdout.write('Options for selecter %s\n' % selecterClassName)
            parser.print_help(file=stdout)
        return None

    try:
        selOptions, selArgs = parser.parse_args(selecterArgs)
    except SystemExit:
        return None

    # FIXME: handle this nicer, too easy to hit
    if selArgs:
        print "WARNING: make sure you specify options with dashes"
        print "Did not parse %r" % selArgs

    return selecterClass(selOptions, database=database)


_DEFAULT_LOOPS = -1
_DEFAULT_RANDOM = True

# _DEFAULT_TRACKS = 'tracks.pickle'


class Selected(object):
    """
    I represent a selected object.
    """
    path = None
    trackmix = None
    number = None

    artists = None
    title = None

    def __init__(self, path, trackmix, number=None, artists=None, title=None):
        self.path = path
        self.trackmix = trackmix
        self.number = number
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

    Initialize me with an options provided by an OptionParser.

    Set me up by calling setup(), then use select() to select a track.
    """
    logCategory = 'selecter'

    option_parser_class = OptionParser

    # loadDeferred should return a count of tracks loaded
    # set by subclass when a complete load is in progress in backend
    loadDeferred = None


    def __init__(self, options, database=None):
        self._selected = [] # list of internally Selected objects

        if not options:
            parser = self.option_parser_class()
            options, _ = parser.parse_args([])
        self.options = options

        self._number = 0

        # FIXME: publicize
        self._loop = 0
        self._loops = options.loops


    ### base method implementations

    # FIXME: decide if we want get or select as our public interface
    def get(self):
        """
        Get a selected track, possibly waiting to (re)query the backend.

        @rtype: L{defer.deferred} firing L{Selected}
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

            def loadCb(result):
                self.debug('get(): loaded, result %r', result)
                if not result:
                    raise KeyError('No tracks loaded')

                self.debug('get(): loaded, returning a recursive get')
                # recursively get
                d2 = self.get()
                d2.addCallback(lambda r: d.callback(r))
                return d2
            self.loadDeferred.addCallback(loadCb)
            self.loadDeferred.addErrback(log.warningFailure, swallow=False)
            self.loadDeferred.addErrback(lambda failure: d.errback(failure))

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

        @rtype: L{defer.deferred} firing L{Selected}
        """
        if not self._selected:
            return None

        selected = self._selected[0]
        del self._selected[0]

        self.debug('getNow: returning %d: %r', selected.number, selected)
        return selected

    def select(self):
        """
        Select the next track to play.


        @rtype: L{Selected}
        """
        d = self.get()

        def _getCb(result):
            self.info('selected %r', result)
            if not result:
                return None
            if not os.path.exists(result.path):
                self.warning('path %r does not exist', result.path)
                print 'WARNING: path %r does not exist' % result.path
            return result
        d.addCallback(_getCb)

        return d

    # FIXME: doesn't seem to be used
    def selectNow(self):
        t = self.getNow()
        if t:
            self.info('selected %r', t)
        else:
            self.info('could not select a track now')
        return t

    def unselect(self, counter):
        """
        Unselect all tracks from the given counter on.

        Used by scheduler to inform us that previously selected tracks
        have been discarded and their history should not be taken into
        account.
        """
        pass

    ### methods for subclasses
    def selected(self, selected):
        """
        Called by subclass when a track has been selected.
        """
        assert isinstance(selected, Selected)
        self._number += 1
        selected.number = self._number
        self.debug('selected: selected %d: %r', selected.number, selected)
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
        self._loop += 1
        self.debug('setup')
        return self.load()

    def load(self):
        """
        Load all tracks to be scheduled.

        @returns: a deferred firing True if tracks could be loaded.
        @rtype:   L{defer.Deferred} firing bool
        """
        raise NotImplementedError

    def setFlavor(self, flavor):
        pass

    def getFlavors(self):
        pass


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

    def __init__(self, options, database=None):
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

_DEFAULT_MY_HOSTNAME = unicode(socket.gethostname())

database_selecter_option_list = [
    optparse.Option('-e', '--extensions',
        action="store", dest="extensions",
        help="file extensions to allow scheduling",
        default=None),
    optparse.Option('-m', '--my-hostname',
        action="store", dest="my_hostname",
        help="my own hostname (defaults to %default)",
        default=_DEFAULT_MY_HOSTNAME),
]

class DatabaseSelecter(Selecter):
    """
    Abstract base class for selecters using the database.
    """

    logCategory = 'databaseselecter'

    # FIXME: can we get around not passing database explicitly ?
    def __init__(self, options, database):
        Selecter.__init__(self, options)
        self._database = database

        self._host = options.my_hostname
        self.debug('Selecting for my hostname %r', self._host)
        exts = options.extensions
        self._extensions = exts and exts.split(',') or []
        self.debug('Selecting extensions: %r', self._extensions)

        # list of L{TrackModel}; private cache of selected tracks
        self._tracks = []

    def load(self):
        return self._loadLimited(10)

    def _loadLimited(self, limit):
        # get a few results as fast as possible
        d = self.getTracks(limit)
        d.addCallback(self.processTracks, self._host)
        def eb(f):
            log.warningFailure(f)
            return f
        d.addErrback(eb)

        # we won't wait on this one; it's an internal deferred to get
        # all items which is slower
        # FIXME: also gets some we already have, filter them somehow ?

        self.loadDeferred = self.getTracks()
        self.loadDeferred.addCallback(self.processTracks, self._host,
            resetLoad=True)
        self.debug('setting loadDef to %r', self.loadDeferred)

        return d


    def unselect(self, counter):
        self.debug('unselect from counter %r', counter)
        del self._tracks[counter:]

    def processTracks(self, gen, host, resetLoad=False):
        """
        @param gen: a generator of L{Track}
        """
        if resetLoad:
            self.debug('setting loadDef to None')
            self.loadDeferred = None

        self.debug('Got playlist generator %r', gen)


        alreadyPlayed = []

        candidates = 0
        local = 0
        kept = 0

        # FIXME: this logic about selecting should go somewhere else ?
        for track in gen:
            candidates += 1
            if track not in self._tracks:
                # make sure the track is here
                best = track.getFragmentFileByHost(host,
                    extensions=self._extensions)
                if not best:
                    self.debug('track %r not on host %r for given extensions'
                        ', skipping',
                        track, host)
                    continue

                local += 1

                artists = track.getArtistNames()

                # make sure we didn't just play a track by any of the artists
                artistReused = False
                if self._tracks:
                    size = min(len(self._tracks), 5)
                    previousArtists = []
                    for t, fr, fi in self._tracks[-size:]:
                        previousArtists.extend(t.getArtistNames())

                    for a in previousArtists:
                        if a in artists:
                            self.debug('Already played track by %r', a)
                            # FIXME: put on reuse pile ?
                            alreadyPlayed.append((track, best))
                            artistReused = True

                if artistReused:
                    continue

                fragment, file = best
                kept += 1
                artists.sort()
                self.debug('Got track %d: %r - %r', kept, track.getName(),
                    artists)
                self._tracks.append((track, fragment, file))
                trackmix = fragment.getTrackMix()

                # FIXME: make this fail, then clean up all twisted warnings
                s = Selected(file.info.path, trackmix, artists=artists,
                    title=track.getName())
                self.selected(s)
                self.debug('couch selecter selected %r', s)

        self.debug('%d candidates, %d local, %d kept', candidates, local, kept)

        # FIXME: arbitrary limit
        if kept < 3:
            self.warning('Only have %d kept tracks', kept)
            if alreadyPlayed:
                self.warning('Picking extra from the pile of alreadyPlayed')

                if len(alreadyPlayed) > 3:
                    alreadyPlayed = alreadyPlayed[:3]

                for track, best in alreadyPlayed:
                    kept += 1
                    fragment, file = best
                    self._tracks.append((track, fragment, file))
                    trackmix = fragment.getTrackMix()

                    s = Selected(file.info.path, trackmix, artists=artists,
                        title=track.getName())
                    self.selected(s)
                    self.debug('couch selecter selected %r', s)


        if kept == 0:
            return False

        return True

_DEFAULT_ABOVE = 0.7
_DEFAULT_BELOW = 1.0
_DEFAULT_CATEGORY = 'Good'
_DEFAULT_USER = getpass.getuser()

score_selecter_option_list = [
    optparse.Option('-u', '--user',
        action="store", dest="user",
        help="user (defaults to current user %default)",
        default=_DEFAULT_USER),
   optparse.Option('-c', '--category',
        action="store", dest="category",
        help="category to make playlist for (defaults to %default)",
        default=_DEFAULT_CATEGORY),
    optparse.Option('-a', '--above',
        action="store", dest="above", type="float",
        help="lower bound for scores (defaults to %default)",
        default=_DEFAULT_ABOVE),
    optparse.Option('-b', '--below',
        action="store", dest="below", type="float",
        help="upper bound for scores (defaults to %default)",
        default=_DEFAULT_BELOW),
]


class DatabaseCategoryOptionParser(OptionParser):
    standard_option_list = OptionParser.standard_option_list + \
        database_selecter_option_list + score_selecter_option_list


class DatabaseCategorySelecter(DatabaseSelecter):

    option_parser_class = DatabaseCategoryOptionParser

    logCategory = 'databaseselector'

    # FIXME: can we get around not passing database explicitly ?
    def __init__(self, options, database):
        DatabaseSelecter.__init__(self, options, database)

        self._category = options.category
        self._user = options.user
        self.debug('Selecting for user %r', self._user)
        self._above = options.above
        self._below = options.below
        self._random = options.random
        self.debug('Selecting randomly: %r', self._random)

    def getTracks(self, limit=None):
        """
        @rtype: a deferred for a generator of L{Track}
        """
        return self._database.getPlaylist(self._host, self._user,
            self._category,
            self._above, self._below, limit=limit, randomize=self._random)


    def getFlavors(self):
        return [
            ('Good', 'good songs'),
            ('Sleep', 'sleepy songs'),
            ('Rock', 'rock songs'),
        ]


    def setFlavor(self, flavor):
        self.debug('setting flavor %r', flavor)
        self._category = flavor
        self._tracks = []
        # FIXME: don't poke privately
        self._selected = []
        self.setup()

selection_selecter_option_list = [
    optparse.Option('-s', '--selection',
        action="store", dest="selection",
        help="selection to play"),
]


class DatabaseSelectionOptionParser(OptionParser):
    standard_option_list = OptionParser.standard_option_list + \
        database_selecter_option_list + selection_selecter_option_list


class DatabaseSelectionSelecter(DatabaseSelecter):

    option_parser_class = DatabaseSelectionOptionParser

    logCategory = 'databaseselectionselector'

    def __init__(self, options, database):
        DatabaseSelecter.__init__(self, options, database)

        self._selection = options.selection
        self.debug('Selecting for selection %r', self._selection)

    @defer.inlineCallbacks
    def getTracks(self, limit=None):
        """
        @rtype: a deferred for a generator of L{Track}
        """
        sm = yield self._database.getSelection(self._selection)

        gen = yield sm.get()

        if limit:
            gen = (t for n, t in enumerate(gen) if n < limit)

        defer.returnValue(gen)


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
