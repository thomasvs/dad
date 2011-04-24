# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base

# move to base class
class SelectorController(base.Controller):
    def __init__(self, model):
        base.Controller.__init__(self, model)

        from twisted.internet import reactor
        self._reactor = reactor

    def populate(self):
        self.debug('populate()')
        self.doViews('throb', True)

        # populate with the iterable we get from the model
        d = self._model.get()

        def cb(iterable):
            # iterable can be generator
            #self.debug('got results: %r' % len(iterable))
            self.debug('populating')

            # space out add_artist calls from the iterator in blocks of a given
            # size; this allows the throbber to update
            def space(iterator, size=1):
                for i in range(size):
                    try:
                        item = iterator.next()
                    except StopIteration:
                        self.doViews('throb', False)
                        self.debug('filled view')
                        return

                    self.addItem(item)
                self._reactor.callLater(0, space, iterator, size)

            self._reactor.callLater(0, space, iter(iterable), size=11)
            self.debug('populated')
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

    def addItem(self, item):
        # tracks can be 0 for Various Artists for example, which own albums
        # but no tracks
        if item.tracks == 0:
            return

        self.doViews('add_row', item.id, "%s (%d)" % (item.name, item.tracks),
            item.sortname, item.tracks)

class AlbumSelectorController(SelectorController):

    logCategory = 'albumSC'

    def addItem(self, item):
        # add an album and the count of tracks on it
        self.doViews('add_row', item.id, "%s (%d)" % (item.name, item.tracks),
            item.sortname, item.tracks)

class TrackSelectorController(SelectorController):

    logCategory = 'trackSC'

    def addItem(self, item):
        # add a track
        self.doViews('add_item', item, [a.name for a in item.artists],
            "%s" % item.name, None, None, None)
