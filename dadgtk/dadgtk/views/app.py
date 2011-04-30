# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import gobject
import gtk

from dad.base import app

class GTKAppView(app.AppView):

    def __init__(self):
        window = gtk.Window()
    
        window.set_default_size(640, 480)

        window.show_all()

        self.widget = window

    def add(self, view):
        self.widget.add(view.widget)
        
