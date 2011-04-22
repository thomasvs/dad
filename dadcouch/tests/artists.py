# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# twisted.web.http imports reactor
# FIXME: fix that so we can move this install to main
from twisted.internet import gtk2reactor
gtk2reactor.install()

# artist selector

import os
import sys
import optparse

import gtk

from dad.base import base
from dad.extern.log import log

from dadcouch.model import daddb
from dadcouch.selecter import couch

from dadcouch.extern.paisley import client

from dadgtk.views import views, scheduler

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
            label = gtk.Label("%r: %r" % (failure, failure.value.args))
            dialog = gtk.Dialog("failed to populate",
                               None,
                               gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                               (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            dialog.vbox.pack_start(label)
            label.show()
            response = dialog.run()
            dialog.destroy()
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


def main():
    from twisted.internet import reactor

    from twisted.internet import defer
    defer.Deferred.debug = 1

    log.init('DAD_DEBUG')
    log.logTwisted()
    log.debug('main', 'start')

    parser = optparse.OptionParser()
    parser.add_options(couch.couchdb_option_list)
    options, args = parser.parse_args()

    # this rebinds and makes it break in views
    # db = client.CouchDB('localhost', dbName='dad')
    cache = client.MemoryCache()
    server = client.CouchDB(host=options.host, port=options.port, cache=cache)
    dbName = options.database
    db = daddb.DADDB(server, dbName)

    window = gtk.Window()
    window.connect('destroy', gtk.main_quit)

    vbox = gtk.VBox()

    hbox = gtk.HBox()

    vbox.add(hbox)

    window.add(vbox)

    artistView = views.ArtistSelectorView()
    artistModel = daddb.ArtistSelectorModel(db)
    artistController = ArtistSelectorController(artistModel)
    artistController.addView(artistView)
    hbox.pack_start(artistView)

    albumView = views.AlbumSelectorView()
    albumModel = daddb.AlbumSelectorModel(db)
    albumController = AlbumSelectorController(albumModel)
    albumController.addView(albumView)
    hbox.pack_start(albumView)

    trackView = scheduler.TracksUI()
    trackModel = daddb.TrackSelectorModel(db)
    trackController = TrackSelectorController(trackModel)
    trackController.addView(trackView)

    vbox.add(trackView)


    # listen to changes on artist selection so we can filter the albums view
    def artist_selected_cb(self, ids):
        import code; code.interact(local=locals())
        album_ids = albumModel.get_artists_albums(ids)
        albumView.set_album_ids(album_ids)

    artistView.connect('selected', artist_selected_cb)


    window.set_default_size(640, 480)

    window.show_all()

    # start loading artists and albums

    d = defer.Deferred()

    d.addCallback(lambda _: artistController.populate())
    d.addCallback(lambda _: albumController.populate())
    d.addCallback(lambda _: trackController.populate())

    d.callback(None)

    reactor.run()

if __name__ == '__main__':
    main()
