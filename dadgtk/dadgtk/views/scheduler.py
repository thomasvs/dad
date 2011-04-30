# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import gobject
import gtk

from dad.extern.log import log

# FIXME: rename SCHEDULED to ID or OBJECT
(
    COLUMN_SCHEDULED,
    COLUMN_ARTISTS,
    COLUMN_ARTIST_IDS,
    COLUMN_TITLE,
    COLUMN_SORT,
    COLUMN_PATH,
    COLUMN_START,
    COLUMN_END
) = range(8)

class TracksUI(gtk.VBox, log.Loggable):
    logCategory = 'tracksui'

    __gsignals__ = {
        'clicked':
            (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, ))
    }

    _artist_ids = None

    def __init__(self, selector=False):
        gtk.VBox.__init__(self)

        self._selector = selector
        self._first_iter = None
        self._count = 0

        self._filter_count = 0
        self._create_store()

        self._treeview = gtk.TreeView(self._store)
        self._add_columns()
        self._treeview.props.rules_hint = True

        sw = gtk.ScrolledWindow()
        self.add(sw)
   
        self._treeview.connect('row_activated', self._treeview_clicked_cb)

        sw.add(self._treeview)

        self._treerowrefs = {} # Scheduled -> gtk.TreeRowReference

        # filtering
        def match_artist_ids(model, iter):
            self._filter_count += 1
            # the first iter always should be shown, as it gives totals
            if model.get_path(iter) == (0, ):
                return True

            # if no album_ids filter is set, everything should be shown
            if self._artist_ids is None:
                return True

            # only show tracks matching the current selection
            value = model.get_value(iter, COLUMN_ARTIST_IDS)
            for v in value or []:
                if v in self._artist_ids:
                    return True

            self._filter_count -= 1
            return False

        self._filter = self._store.filter_new(root=None)
        self._filter.set_visible_func(match_artist_ids)
        self._treeview.set_model(self._filter)


    def _create_store(self):
        self._store = gtk.ListStore(
            object,
            gobject.TYPE_STRING,
            object,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            )


        if self._selector:
            self._first_iter = self._store.append()
            self._show_count()

    def _show_count(self, tracks=None):
        count = tracks or self._count
        self._store.set(self._first_iter,
            COLUMN_TITLE, "All %d tracks" % count,
            COLUMN_SORT, "")

    def _scheduled_cb(self, scheduler, scheduled):
        self.add_scheduled(scheduled)

    def add_item(self, item, artists, artist_ids, title, path, start, end):
        """
        """
        #self.debug('add: adding %r', item)
        iter = self._store.append()
        self._store.set(iter,
            COLUMN_SCHEDULED, item,
            COLUMN_ARTISTS, "\n".join(artists),
            COLUMN_ARTIST_IDS, artist_ids,
            COLUMN_TITLE, title,
            COLUMN_SORT, title,
            COLUMN_PATH, path,
            COLUMN_START, start,
            COLUMN_END, end
        )
        # self._treeview.set_model(self._store)
        self._treerowrefs[item] = gtk.TreeRowReference(
            self._store, self._store.get_path(iter))

        self._count += 1
        if self._selector:
            self._show_count()

    def _add_columns(self):
        column = gtk.TreeViewColumn('Artists', gtk.CellRendererText(),
                                    text=COLUMN_ARTISTS)
        self._treeview.append_column(column)

        column = gtk.TreeViewColumn('Title', gtk.CellRendererText(),
                                    text=COLUMN_TITLE)
        self._treeview.append_column(column)
        # this may be a bit slow ?
        #if self._selector:
        #    self._store.set_sort_column_id(COLUMN_SORT, gtk.SORT_ASCENDING)

        # do not show path now that we have artist and title
        # column = gtk.TreeViewColumn('Path', gtk.CellRendererText(),
        #                             text=COLUMN_PATH)
        # self._treeview.append_column(column)

        # column = gtk.TreeViewColumn('Start', gtk.CellRendererText(),
        #                             text=COLUMN_START)
        # self._treeview.append_column(column)
    
        # column = gtk.TreeViewColumn('End', gtk.CellRendererText(),
        #                             text=COLUMN_END)
        # self._treeview.append_column(column)
 
    def _treeview_clicked_cb(self, tv, path, column):
        iter = self._filter.get_iter(path)
        item = self._filter.get_value(iter, COLUMN_SCHEDULED)
        self.emit('clicked', item)

    def throb(self, active=True):
        print 'THOMAS: FIXME: throb', active

    def set_artist_ids(self, ids):
        """
        Filter the view with tracks only from the given artists.
        """
        for i in ids:
            assert type(i) is unicode, "artist id %r is not unicode" % i

        # used when an artist is selected and only its tracks
        self.debug('set_artist_ids: %r', ids)
        self._artist_ids = ids
        self._filter_count = 0
        self._filter.refilter()

        if ids is None:
            # all selected
            self._show_count()
        else:
            # update count to show filtered results
            # FIXME: this formula determined by experimentation
            self._show_count((self._filter_count -1) / 2)

        # reselect the first
        # self._selection.select_path((0, ))        

class SchedulerUI(TracksUI):
    logCategory = 'schedulerui'

    def set_scheduler(self, scheduler):
        """
        Call me before any tracks get scheduled.
        """
        self.debug('set_scheduler: %r', scheduler)
        scheduler.connect('scheduled', self._scheduled_cb)

    def _scheduled_cb(self, scheduler, scheduled):
        self.add_scheduled(scheduled)

    # call me to indicate a scheduled item has started playing
    def started(self, scheduled):
        # FIXME: instead of printing, signal to the command ui
        print '\rstarted', scheduled
        path = self._treerowrefs[scheduled].get_path()
        ts = self._treeview.get_selection()
        ts.select_path(path)

    def add_scheduled(self, scheduled):
        """
        @type  scheduled: L{scheduler.Scheduled}
        """
        import gst
        self.debug('add_scheduled: adding %r', scheduled)
        self.add_item(scheduled, scheduled.artists,
            [], scheduled.title or scheduled.description,
            scheduled.path,
            gst.TIME_ARGS(scheduled.start),
            gst.TIME_ARGS(scheduled.start + scheduled.duration))

gobject.type_register(SchedulerUI)

def main():
    window = gtk.Window()

    s = SchedulerUI()

    window.add(s)
    window.connect('destroy', lambda _: gtk.main_quit())

    window.show_all()

if __name__ == "__main__":
    main()
    gtk.main()

