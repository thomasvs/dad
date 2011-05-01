# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import glib
import gobject
import gtk

from dad.base import base

from dadgtk.views import views
from dadgtk.views import track


class AlbumView(views.GTKView, track.ScorableView):

    subject_type = 'album'

    def __init__(self):
        track.ScorableView.__init__(self)

        self._builder = gtk.Builder()
        path = os.path.join(os.path.dirname(__file__), "album-info.ui") 
        self._builder.add_from_file(path)
        self.widget = self._builder.get_object("album_info")

        self.init_score()

    def set_name(self, name):
        entry = self._builder.get_object("album_info_name")
        entry.set_text(name)

    def set_artist(self, name):
        entry = self._builder.get_object("album_info_artist")
        entry.set_text(name)

if __name__ == '__main__':
    view = AlbumView()

    window = gtk.Window()
    window.connect('destroy', gtk.main_quit)

    window.add(view.widget)

    window.show()

    view.set_artist('Tool')
    view.set_title('Aenema')

    view.set_score('Good', 0.8)
    view.set_score('Rock', 0.8)

    def scored_cb(_, category, value):
        print 'emit category %r value %r' % (category, value)

    view.connect('scored', scored_cb)

    gtk.main()
