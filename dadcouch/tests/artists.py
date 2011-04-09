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


from dad.base import base
from dad.extern.log import log

from dadcouch.model import daddb
from dadcouch.selecter import couch

from dadcouch.extern.paisley import client, views

# should move to gtk part

import gobject
import gtk

(
    COLUMN_ID,
    COLUMN_DISPLAY,
    COLUMN_SORT,
    COLUMN_TRACKS,
) = range(4)

class GTKSelectorView(gtk.VBox, base.SelectorView):
    """
    I am a selector widget for a list of objects.

    I wrap a tree view with a single visible column, and an invisible sort
    column.
    I also have a throbber next to the title button.
    """

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

    ### SelectorView implementations
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


class ArtistSelectorView(GTKSelectorView):

    title = 'Artists'
    first = 'All %d artists'

class AlbumSelectorView(GTKSelectorView):

    title = 'Albums'
    first = 'All %d albums'

    _album_ids = None

    def __init__(self):
        GTKSelectorView.__init__(self)

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


def main():
    from twisted.internet import reactor

    from twisted.internet import defer
    defer.Deferred.debug = 1

    log.init('DAD_DEBUG')
    log.debug('main', 'start')

    parser = optparse.OptionParser()
    parser.add_options(couch.couchdb_option_list)
    options, args = parser.parse_args()

    # this rebinds and makes it break in views
    # db = client.CouchDB('localhost', dbName='dad')
    server = client.CouchDB(host=options.host, port=options.port)
    dbName = options.database

    window = gtk.Window()

    box = gtk.HBox()

    window.add(box)

    artistView = ArtistSelectorView()
    artistModel = daddb.ArtistSelectorModel(server, dbName)
    artistController = ArtistSelectorController(artistModel)
    artistController.addView(artistView)
    box.pack_start(artistView)

    albumView = AlbumSelectorView()
    albumModel = daddb.AlbumSelectorModel(server, dbName)
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

    reactor.run()

if __name__ == '__main__':
    main()
