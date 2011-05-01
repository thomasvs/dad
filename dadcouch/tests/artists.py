# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# twisted.web.http imports reactor
# FIXME: fix that so we can move this install to main
from dadgtk.twisted import gtk2reactor
gtk2reactor.install()

# artist selector

import os
import sys
import optparse

import gtk

from twisted.python import reflect

from dad.base import base, app
from dad.extern.log import log
from dad.controller import selector
from dad.controller import track as trackc

from dadcouch.model import daddb
from dadcouch.selecter import couch

from dadcouch.extern.paisley import client

from dadgtk.views import views, scheduler

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

    # FIXME: allow customizing model and/or view(s)
    modelType = 'Couch'
    viewTypes = ['GTK', ]

    # this rebinds and makes it break in views
    # db = client.CouchDB('localhost', dbName='dad')
    cache = client.MemoryCache()
    server = client.CouchDB(host=options.host, port=options.port, cache=cache)
    dbName = options.database
    db = daddb.DADDB(server, dbName)


    # cache artists
    from dadcouch.model import couch as mcouch
    d = db.viewDocs('artists', mcouch.Artist)
    def cacheCb(_):
        print 'THOMAS: cache: hits %r lookups %r' % (
            db.db._cache.hits, db.db._cache.lookups)
    d.addCallback(cacheCb)

    modelModule = 'dad%s.models.app.%sAppModel' % (modelType.lower(), modelType)
    amodel = reflect.namedAny(modelModule)(db)

    acontroller = app.AppController(amodel)

    for viewType in viewTypes:
        viewModule = 'dad%s.views.app.%sAppView' % (viewType.lower(), viewType)
        aview = reflect.namedAny(viewModule)()
        acontroller.addView(aview)

    # FIXME: gtk-specific
    aview.widget.connect('destroy', lambda _: reactor.stop())


    vbox = gtk.VBox()

    hbox = gtk.HBox()

    vbox.add(hbox)

    aview.widget.add(vbox)

    artistView = views.ArtistSelectorView()
    artistModel = daddb.ArtistSelectorModel(db)
    artistController = selector.ArtistSelectorController(artistModel)
    artistController.addView(artistView)
    acontroller.add(artistController)
    hbox.pack_start(artistView)

    albumView = views.AlbumSelectorView()
    albumModel = daddb.AlbumSelectorModel(db)
    albumController = selector.AlbumSelectorController(albumModel)
    albumController.addView(albumView)
    acontroller.add(albumController)
    hbox.pack_start(albumView)

    trackView = scheduler.TracksUI(selector=True)
    trackModel = daddb.TrackSelectorModel(db)
    trackController = selector.TrackSelectorController(trackModel)
    acontroller.add(trackController)
    trackController.addView(trackView)

    vbox.add(trackView)

    aview.widget.show_all()


    # listen to changes on artist selection so we can filter the albums view
    def artist_selected_cb(self, ids):
        album_ids = []
        if ids:
            print 'THOMAS: selected artist ids', ids
            album_ids = albumModel.get_artists_albums(ids)
        albumView.set_album_ids(album_ids)

        trackView.set_artist_ids(ids)

    artistView.connect('selected', artist_selected_cb)

    def track_selected_cb(self, trackObj):
        w = gtk.Window()

        from dadgtk.views import track
        view = track.TrackView()

        w.add(view.widget)


        model = daddb.TrackModel(db)
        controller = trackc.TrackController(model)
        controller.addView(view)
        # FIXME: don't hardcode
        options.user = 'thomas'
        d = controller.populate(trackObj.id, userName=options.user)
        d.addCallback(lambda _: w.set_title(trackObj.name))

        w.show_all()



 

    trackView.connect('clicked', track_selected_cb)

    # start loading artists and albums

    d = defer.Deferred()

    d.addCallback(lambda _: artistController.populate())
    d.addCallback(lambda _: albumController.populate())
    d.addCallback(lambda _: trackController.populate())
    d.addCallback(cacheCb)

    d.callback(None)

    reactor.run()

if __name__ == '__main__':
    main()
