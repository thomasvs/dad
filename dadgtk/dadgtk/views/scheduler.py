# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import gst
import gobject
import gtk

from gst.extend import pygobject

from dad.extern.log import log

# FIXME: rename SCHEDULED to ID or OBJECT
(
    COLUMN_SCHEDULED,
    COLUMN_ARTISTS,
    COLUMN_TITLE,
    COLUMN_PATH,
    COLUMN_START,
    COLUMN_END
) = range(6)

class TracksUI(gtk.TreeView, log.Loggable):
    logCategory = 'tracksui'

    pygobject.gsignal('clicked', object)

    def __init__(self):
        gtk.Widget.__init__(self)

        self._store = gtk.ListStore(
            object,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            )

        self._treeview = self # gtk.TreeView()

        column = gtk.TreeViewColumn('Artists', gtk.CellRendererText(),
                                    text=COLUMN_ARTISTS)
        self._treeview.append_column(column)

        column = gtk.TreeViewColumn('Title', gtk.CellRendererText(),
                                    text=COLUMN_TITLE)
        self._treeview.append_column(column)

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
    
        self._treeview.connect('row_activated', self._treeview_clicked_cb)

        self._treerowrefs = {} # Scheduled -> gtk.TreeRowReference

    def _scheduled_cb(self, scheduler, scheduled):
        self.add_scheduled(scheduled)

    def add(self, item, artists, title, path, start, end):
        """
        """
        self.debug('add: adding %r', item)
        iter = self._store.append()
        self._store.set(iter,
            COLUMN_SCHEDULED, item,
            COLUMN_ARTISTS, "\n".join(artists),
            COLUMN_TITLE, title,
            COLUMN_PATH, path,
            COLUMN_START, start,
            COLUMN_END, end
        )
        self._treeview.set_model(self._store)
        self._treerowrefs[item] = gtk.TreeRowReference(
            self._store, self._store.get_path(iter))

    def _treeview_clicked_cb(self, tv, path, column):
        iter = self._store.get_iter(path)
        item = self._store.get_value(iter, COLUMN_SCHEDULED)
        self.emit('clicked', item)

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
        self.debug('add_scheduled: adding %r', scheduled)
        self.add(scheduled, scheduled.artists,
            scheduled.title or scheduled.description,
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

