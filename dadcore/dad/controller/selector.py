# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.base import base

# move to base class
class SelectorController(base.Controller):
    def __init__(self, model):
        base.Controller.__init__(self, model)

        from twisted.internet import reactor
        self._reactor = reactor

    def populate(self):
        self.debug('populate() using model %r', self._model)
        self.doViews('throb', True)

        # populate with the iterable we get from the model
        d = self._model.get()

        # a contaxt to track the view deferred and item count
        class Context:
            def __init__(self):
                self.viewD = defer.Deferred()
                self.i = 0

        def cb(iterable):
            # iterable can be generator
            #self.debug('got results: %r' % len(iterable))
            self.debug('populating')

            # space out add_artist calls from the iterator in blocks of a given
            # size; this allows the throbber to update
            def space(iterator, ctx, size=1):
                for i in range(size):
                    try:
                        item = iterator.next()
                        ctx.i += 1
                    except StopIteration:
                        self.doViews('throb', False)
                        self.debug('filled view with %d items', ctx.i)
                        ctx.viewD.callback(None)
                        return

                    self.addItem(item)
                self._reactor.callLater(0, space, iterator, ctx, size)

            ctx = Context()
            self._reactor.callLater(0, space, iter(iterable), ctx, size=11)
            self.debug('populated')
            return ctx.viewD
        d.addCallback(cb)

        def eb(failure):
            self.warningFailure(failure)
            self.doViews('error', "failed to populate",
                "%r: %r" % (failure, failure.value.args))
        d.addErrback(eb)

        return d

    def addItem(self, item):
        raise NotImplementedError, \
            "implement addItem using self.doViews('add_row', ...)"

class ArtistSelectorController(SelectorController):

    logCategory = 'artistSC'

    @defer.inlineCallbacks
    def addItem(self, item):
        """
        @type  item: subclass of L{dad.model.artist.ArtistModel}
        """

        # tracks can be 0 for Various Artists for example, which own albums
        # but no tracks
        if item.getTrackCount() == 0:
            return

        mid = yield item.getMid()
        name = yield item.getName()
        sortname = yield item.getSortName()
        count = yield item.getTrackCount()
        self.doViews('add_row', item, mid, name, sortname, count)

class AlbumSelectorController(SelectorController):

    logCategory = 'albumSC'

    # FIXME: need an mid
    def addItem(self, item):
        self.debug('addItem: %r', item)
        # add an album and the count of tracks on it
        self.doViews('add_row', item, item.mid, item.name,
            item.sortname, item.tracks)

class TrackSelectorController(SelectorController):

    logCategory = 'trackSC'

    @defer.inlineCallbacks
    def addItem(self, item):
        """
        @type  item: L{dad.model.track.TrackModel}
        """
        # add a track
        self.debug('addItem: %r', item)
        albums = yield item.getAlbums()
        album_mids = [a.getMid() for a in albums]
        self.doViews('add_item', item, item.getArtistNames(),
            item.getArtistMids(),
            "%s" % item.getName(), None, None, None, album_mids)

    def nopopulate(self):
        self.debug('populate()')
        self.doViews('throb', True)

        # populate with the iterable we get from the model
        d = self._model.get(cb=lambda r: self.addItem(r))
        def cb(res):
            self.debug('populated()')
            return res
        d.addCallback(cb)

        return d


