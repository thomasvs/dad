# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import glib
import gobject
import gtk

from dad.base import base


class TrackView(gobject.GObject):

    __gsignals__ = {
        'scored': 
            (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (str, float))
    }

    score_delay = 1 # seconds before emitting scored


    def __init__(self):
        gobject.GObject.__init__(self)

        self._builder = gtk.Builder()
        path = os.path.join(os.path.dirname(__file__), "track-info.ui") 
        self._builder.add_from_file(path)
        self.widget = self._builder.get_object("track_info")

        self._score = self._builder.get_object("track_info_score")
        self._score.foreach(self._score.remove)
        self._scores = {} # category -> widget
        self._timeouts = {} # category -> timeout
 

    
    def set_title(self, title):
        entry = self._builder.get_object("track_info_title")
        entry.set_text(title)

    def set_artist(self, name):
        entry = self._builder.get_object("track_info_artist")
        entry.set_text(name)

    # scores are dynamic
    def set_score(self, category, value):
        if category not in self._scores:
            top = len(self._scores)

            label = gtk.Label(category)
            self._score.attach(label, 0, 1, top, top + 1)
            self._scores[category] = label

            spin = gtk.SpinButton(digits=3)
            spin.set_range(0.0, 1.0)
            spin.set_increments(0.01, 0.1)
            spin.set_value(value)
            spin.connect("value-changed", self._score_changed_cb, category)
            self._score.attach(spin, 1, 2, top, top + 1)

            self._score.show_all()
        
    def _score_changed_cb(self, sb, category):
        value = sb.get_value()

        if category in self._timeouts:
            glib.source_remove(self._timeouts[category])

        i = glib.timeout_add_seconds(self.score_delay, 
            self._emit_score, category, value)
        self._timeouts[category] = i

    def _emit_score(self, category, value):
        self.emit('scored', category, value)

if __name__ == '__main__':
    view = TrackView()

    window = gtk.Window()
    window.connect('destroy', gtk.main_quit)

    window.add(view.widget)

    window.show()

    view.set_artist('Salt n Pepa')
    view.set_title('Push it')

    view.set_score('Good', 0.8)
    view.set_score('Party', 0.7)

    def scored_cb(_, category, value):
        print 'emit category %r value %r' % (category, value)

    view.connect('scored', scored_cb)

    gtk.main()