# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import gobject
import gtk

from dad.base import base

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
