# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import gobject
import gtk

from dad.base import base
from dad.view import selector

(
    COLUMN_MID,
    COLUMN_MODEL,
    COLUMN_DISPLAY,
    COLUMN_SORT,
    COLUMN_TRACKS,
) = range(5)

class Throbber(gtk.Image):
    path = None

    def set_path(self, path):
        self.path = path

    def throb(self, active=True):
        """
        Start or stop throbbing the selector to indicate activity.

        @param active: whether to throb
        """
        path = self.path
        if not path:
            path = os.path.join(os.path.dirname(__file__), '../../data/ui') 

        if active:
            self.set_from_file(os.path.join(path, 'Throbber.gif'))
        else:
            self.set_from_file(os.path.join(path, 'Throbber.png'))


class GTKView(base.View):

    # FIXME: push to base class ?
    def error(self, title, debug):

            label = gtk.Label(debug)
            dialog = gtk.Dialog(title,
                               None,
                               gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                               (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            dialog.vbox.pack_start(label)
            label.show()
            response = dialog.run()
            dialog.destroy()
 

class GTKSelectorView(gtk.VBox, GTKView, selector.SelectorView):
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

    # selected fires with:
    # - None if the first row (ie everything) is selected
    # - [] if nothing is selected
    # - [list of ids] if rows are selected

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

        self.throbber = Throbber()
        self.throbber.throb(False)
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
        self._treeview.connect("popup-menu", self._on_popup_menu_cb)
        self._treeview.connect("button-press-event",
            self._on_button_press_event_cb)

        sw.add(self._treeview)

        self._id_to_tracks = {}

    def _create_store(self):
        self._store = gtk.ListStore(
            object, # best choice for unicode ?
            object,
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

        if not paths:
            self.debug('Nothing selected, returning empty list')
            return []

        ids = []

        for p in paths:
            i = model.get_iter(p)
            # FIXME: getting id back from store is a non-unicode str ?
            itemId = model.get_value(i, COLUMN_MID)
            if itemId:
                ids.append(itemId)

        # if the first row is selected, return None
        if not ids:
            ids = None

        self.debug('Selected %r', ids)

        self.emit('selected', ids)

    def _on_button_press_event_cb(self, treeview, event):
        # single click with the right mouse button?
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self._view_popup_menu(event)

            return True

        return False

    def _on_popup_menu_cb(self, widget):
        self._view_popup_menu(None)

    def _view_popup_menu(self, event):
        sel = self._treeview.get_selection()
        model, paths = sel.get_selected_rows()
        items = []

        for p in paths:
            i = self._treeview.get_model().get_iter(p)
            # FIXME: getting id back from store is a non-unicode str ?
            items.append((
                self._treeview.get_model().get_value(i, COLUMN_MODEL),
                unicode(self._treeview.get_model().get_value(i, COLUMN_DISPLAY)),
            ))

        for (model, name) in items:
            menu = gtk.Menu()
            item = gtk.MenuItem(label='_Info')
            menu.add(item)
            item.connect('activate', self._show_info, model, name)
            menu.popup(None, None, None, event and event.button or None, event.get_time() or 0.0)
            menu.show_all()

    def _show_info(self, item, subject, name):
        self.debug('show info in subject %r', subject)

        controller, model, views = self.controller.getRoot().getTriad(self.what, model=subject)
        w = gtk.Window()
        w.add(views[0].widget)

        # FIXME: don't hardcode username
        # self.debug('asking controller %r to populate', controller)
        d = controller.populate(model, userName='thomas')

        def cb(_):
            w.set_title(model.getName())
        d.addCallback(cb)

        w.show_all()

        

    def _show_count(self, albums=None, tracks=None):
        if albums is None:
            albums = self.count
        if tracks is None:
            tracks = self.track_count

        template = self.first + " (%d)"
        self._store.set(self._first,
            COLUMN_DISPLAY, template % (albums, tracks),
            COLUMN_SORT, None)

    ### selector.SelectorView implementations
    def add_row(self, model, mid, display, sort, tracks):
        assert model, 'artist model %r is empty' % model
        self.log('add_row: model %r, mid %r, display %r', model, mid, display)

        iter = self._store.append()
        self._store.set(iter,
            COLUMN_MID, mid,
            COLUMN_MODEL, model,
            COLUMN_DISPLAY, "%s (%d)" % (display, tracks),
            COLUMN_SORT, sort,
            COLUMN_TRACKS, tracks)
        self.count += 1
        self.track_count += tracks

        self._id_to_tracks[mid] = tracks

        self._show_count()

    def throb(self, active=True):
        """
        Start or stop throbbing the selector to indicate activity.

        @param active: whether to throb
        """
        self.throbber.throb(active)




class ArtistSelectorView(GTKSelectorView):

    title = 'Artists'
    first = 'All %d artists'
    what = 'Artist'

# FIXME: make base class

class AlbumSelectorView(GTKSelectorView):

    title = 'Albums'
    first = 'All %d albums'
    what = 'Album'

    _album_ids = None


    logCategory = 'albumselector'

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
            value = model.get_value(iter, COLUMN_MID)
            return value in self._album_ids

        self._filter = self._store.filter_new(root=None)
        self._filter.set_visible_func(match_album_ids)
        self._treeview.set_model(self._filter)

    def set_album_ids(self, ids):
        """
        Set the ids of albums that this selector view should show.

        @param ids: None if all albums should be shown (no selection),
                    [] if no albums should be shown,
                    or a list of album ids to show.
        @type  ids: list of C{unicode} or None
        """

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
                tracks += self._id_to_tracks.get(i, 0)

            # update count to show filtered results
            self._show_count(len(self._album_ids), tracks)

        # reselect the first
        self._selection.select_path((0, ))
