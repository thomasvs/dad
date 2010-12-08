# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import gtk2reactor
gtk2reactor.install()


# artist selector

import os
import sys

from twisted.python import failure
from twisted.internet import defer

defer.Deferred.debug = 1

from dad.extern.paisley import couchdb, views
from dad.extern.log import log

from dad.model import couch

server = couchdb.CouchDB('localhost')
DB = 'dadtest'

class ItemTracks:
    # map tracks-by-album and tracks-by-artist
    def fromDict(self, d):
        self.type = d['key'][1] # 0 for artist/album row, 1 for trackm row

        v = d['value']

        if self.type == 0:
            # artist/album row, full doc
            self.name = v['name']
            self.sortname = v.get('sortname', v['name'])
            self.id = d['id']

            # will be set in a callback to count tracks on this album
            self.tracks = 0
        else:
            # trackalbum, only track_id
            self.trackId = d['id']

class AlbumsByArtist:
    # map albums-by-artist
    def fromDict(self, d):
        self.type = d['key'][1] # 0 for artist row, 1 for album row

        v = d['value']

        if self.type == 0:
            # artist
            self.name = v['name']
            self.sortname = v.get('sortname', v['name'])
            self.id = d['id']
            self.albums = []
        else:
            # album
            self.albumId = d['id']


class Model(log.Loggable):
    def __init__(self, server, db):
        self._server = server
        self._db = db

class ArtistSelectorModel(Model):
    def get(self):
        """
        @returns: a deferred firing a list of ItemTracks objects representing
                  only artists and their track count.
        """
        self.debug('get')
        v = views.View(self._server, self._db, 'dad', 'tracks-by-artist',
            ItemTracks)
        try:
            d = v.queryView()
        except Exception, e:
            print 'THOMAS: exception', e
            return defer.fail(e)

        def cb(itemTracks):
            # convert list of ordered itemTracks of mixed type
            # into a list of only artist itemTracks with their track count
            ret = []

            artist = None

            for i in itemTracks:
                if i.type == 0:
                    artist = i
                    ret.append(artist)
                else:
                    artist.tracks += 1

            return ret
        d.addCallback(cb)

        def eb(failure):
            print 'THOMAS: Failure:', failure
            return failure
        d.addErrback(eb)

        return d

class AlbumSelectorModel(Model):

    artistAlbums = None # artist id -> album ids

    def get(self):
        """
        @returns: a deferred firing a list of ItemTracks objects representing
                  only albums and their track count.
        """
        self.debug('get')

        d = defer.Deferred()

        # first, load a mapping of artists to albums
        view = views.View(self._server, self._db, 'dad', 'albums-by-artist',
                          AlbumsByArtist)
        d.addCallback(lambda _, v: v.queryView(), view)

        def cb(items):
            self.debug('parsing albums-by-artist')
            # convert list of ordered AlbumsByArtist of mixed type
            # into a list of only album itemTracks with their track count
            artists = []

            album = None

            for i in items:
                if i.type == 0:
                    artist = i
                    artists.append(artist)
                else:
                    artist.albums.append(i)

            self.artistAlbums = {}

            for artist in artists:
                self.artistAlbums[artist.id] = [a.albumId for a in artist.albums]

            return None

        d.addCallback(cb)

        # now, load the tracks per album, and aggregate and return
        view = views.View(self._server, self._db, 'dad', 'tracks-by-album',
                          ItemTracks)
        d.addCallback(lambda _, v: v.queryView(), view)

        def cb(itemTracks):
            self.debug('parsing tracks-by-album')
            # convert list of ordered itemTracks of mixed type
            # into a list of only album itemTracks with their track count
            ret = []

            album = None
            for i in itemTracks:
                if i.type == 0:
                    album = i
                    ret.append(album)
                else:
                    album.tracks += 1

            return ret

        d.addCallback(cb)

        d.callback(None)

        return d

    def get_artists_albums(self, artist_ids):
        """
        @rtype: list of str
        """
        # return a list of album ids for the given list of artist ids
        # returns None if the first total row is selected, ie all artists
        ret = {}

        # first row has totals, and [None}
        if None in artist_ids:
            return None

        for artist in artist_ids:
            for album in self.artistAlbums[artist]:
                ret[album] = 1

        return ret.keys()

import gobject
import gtk

(
    COLUMN_ID,
    COLUMN_DISPLAY,
    COLUMN_SORT,
    COLUMN_TRACKS,
) = range(4)

class SelectorView(gtk.VBox, log.Loggable):
    """
    I am a selector widget for a list of objects.

    I wrap a tree view with a single visible column, and an invisible sort
    column.
    I also have a throbber next to the title button.
    """

    title = 'Selector, override me'
    # FIXME: handle singular/plural properly
    first = 'All %d items'

    count = 0
    track_count = 0

    _id_to_tracks = None # dict of id -> track count

    __gsignals__ = {
        'selected': 
            (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (gobject.TYPE_PYOBJECT, ))
    }

    def __init__(self, throbber_path=None):
        """
        @type throbber_path: str
        """
        gtk.VBox.__init__(self)

        self._first = None # header iter
        self._throbber_path = throbber_path

        self._create_store()

        hbox = gtk.HBox()
        button = gtk.Button()
        button.set_label(self.title)
        hbox.pack_start(button)

        self.pack_start(hbox, expand=False, fill=False)

        self.throbber = gtk.Image()
        self.throb(False)
        hbox.pack_start(self.throbber, expand=False)

        sw = gtk.ScrolledWindow()

        self.pack_start(sw)

        self._treeview = gtk.TreeView(self._store)
        self._add_columns()

        sel = self._treeview.get_selection()
        sel.set_mode(gtk.SELECTION_MULTIPLE)
        sel.select_iter(self._first)
        sel.connect('changed', self._selection_changed_cb)

        self._selection = sel

        self._treeview.set_headers_visible(False)

        sw.add(self._treeview)

        self._id_to_tracks = {}

    def _create_store(self):
        self._store = gtk.ListStore(
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_INT)
        self._store.set_sort_column_id(COLUMN_SORT, gtk.SORT_ASCENDING)
        
    def _add_columns(self):
        # column for display of artist
        column = gtk.TreeViewColumn(self.title, gtk.CellRendererText(),
                                    text=COLUMN_DISPLAY)
        self._treeview.append_column(column)

        self._first = self._store.append()
        self._show_count()

    def _selection_changed_cb(self, sel):
        model, paths = sel.get_selected_rows()
        ids = []

        for p in paths:
            i = self._store.get_iter(p)
            ids.append(self._store.get_value(i, COLUMN_ID))

        self.emit('selected', ids)

    def _show_count(self, albums=None, tracks=None):
        if albums is None:
            albums = self.count
        if tracks is None:
            tracks = self.track_count

        template = self.first + " (%d)"
        self._store.set(self._first,
            COLUMN_DISPLAY, template % (albums, tracks),
            COLUMN_SORT, None)

    def add_row(self, i, display, sort, tracks):
        iter = self._store.append()
        self._store.set(iter,
            COLUMN_ID, i,
            COLUMN_DISPLAY, display,
            COLUMN_SORT, sort,
            COLUMN_TRACKS, tracks)
        self.count += 1
        self.track_count += tracks

        self._id_to_tracks[i] = tracks

        self._show_count()

    def throb(self, active=True):
        """
        Start or stop throbbing the selector to indicate activity.

        @param active: whether to throb
        """
        path = self._throbber_path
        if not path:
            path = os.path.join(os.path.dirname(__file__), '../data/ui') 

        if active:
            self.throbber.set_from_file(os.path.join(path, 'Throbber.gif'))
        else:
            self.throbber.set_from_file(os.path.join(path, 'Throbber.png'))


class ArtistSelectorView(SelectorView):

    title = 'Artists'
    first = 'All %d artists'

class AlbumSelectorView(SelectorView):

    title = 'Albums'
    first = 'All %d albums'

    _album_ids = None

    def __init__(self):
        SelectorView.__init__(self)

        # filtering
        def match_album_ids(model, iter):
            # the first iter always should be shown, as it gives totals
            if model.get_path(iter) == (0, ):
                return True

            # if no album_ids filter is set, everything should be shown
            if self._album_ids is None:
                return True

            # only show albums matching the current selection
            value = model.get_value(iter, COLUMN_ID)
            return value in self._album_ids

        self._filter = self._store.filter_new(root=None)
        self._filter.set_visible_func(match_album_ids)
        self._treeview.set_model(self._filter)

    def set_album_ids(self, ids):
        # used when an artist is selected and only its albums should be shown
        self.debug('set_album_ids: %r', ids)
        self._album_ids = ids
        self._filter.refilter()

        if ids is None:
            # all selected
            self._show_count()
        else:
            tracks = 0
            for i in ids:
                tracks += self._id_to_tracks[i]

            # update count to show filtered results
            self._show_count(len(self._album_ids), tracks)

        # reselect the first
        self._selection.select_path((0, ))

class SelectorController(log.Loggable):
    def __init__(self, model):
        self._model = model
        self._views = []

    def addView(self, view):
        self._views.append(view)

    def doViews(self, method, *args, **kwargs):
        for view in self._views:
            m = getattr(view, method)
            m(*args, **kwargs)

    def populate(self):
        self.debug('populate()')
        self.doViews('throb', True)

        # populate with the iterable we get from the model
        d = self._model.get()

        def cb(iterable):
            self.debug('got results: %r' % len(iterable))
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
                reactor.callLater(0, space, iterator, size)

            reactor.callLater(0, space, iter(iterable), size=11)
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


def main():
    log.init('DAD_DEBUG')
    log.debug('main', 'start')

    server = 'localhost'
    if len(sys.argv) > 1:
        server = sys.argv[1]

    db = 'dad'
    if len(sys.argv) > 2:
        db = sys.argv[2]

    # this rebinds and makes it break in views
    # db = couchdb.CouchDB('localhost', dbName='dad')
    server = couchdb.CouchDB(server)

    window = gtk.Window()

    box = gtk.HBox()

    window.add(box)

    artistView = ArtistSelectorView()
    artistModel = ArtistSelectorModel(server, db)
    artistController = ArtistSelectorController(artistModel)
    artistController.addView(artistView)
    box.pack_start(artistView)

    albumView = AlbumSelectorView()
    albumModel = AlbumSelectorModel(server, db)
    albumController = AlbumSelectorController(albumModel)
    albumController.addView(albumView)
    box.pack_start(albumView)

    # listen to changes on artist selection so we can filter the albums view
    def artist_selected_cb(self, ids):
        album_ids = albumModel.get_artists_albums(ids)
        albumView.set_album_ids(album_ids)

    artistView.connect('selected', artist_selected_cb)


    window.set_default_size(640, 480)

    window.show_all()

    # start loading artists and albums
    artistController.populate()
    albumController.populate()


from twisted.internet import reactor

main()

reactor.run()

