# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os

import gst
import gobject
import gtk

from gst.extend import pygobject

from dad.extern.log import log

from dad.common import formatting

class SeekUI(gtk.Table, log.Loggable):
    """
    I am a seek bar to seek in the currently playing track, as well as the
    whole playlist past and future.
    """
    logCategory = 'seekui'

    pygobject.gsignal('seeked-track', float)
    pygobject.gsignal('seeked-schedule', float)

    def __init__(self):
        gtk.Table.__init__(self, rows=2, columns=2)

        self._track_scale = gtk.HScale()
        self.attach(self._track_scale, 0, 1, 0, 1, yoptions=gtk.SHRINK,
            xpadding=6, ypadding=6)
        self._track_label = gtk.Label('--:--:--')
        self.attach(self._track_label, 1, 2, 0, 1,
            xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=6, ypadding=6)
        self._track_scale.connect('change-value', self._track_changed_cb)
        self._track_scale.connect('format-value', lambda _, v: formatting.formatTime(v))

        self._schedule_scale = gtk.HScale()
        self.attach(self._schedule_scale, 0, 1, 1, 2, yoptions=gtk.SHRINK,
            xpadding=6, ypadding=6)
        self._schedule_label = gtk.Label('--:--:--')
        self.attach(self._schedule_label, 1, 2, 1, 2,
            xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=6, ypadding=6)
        self._schedule_scale.connect('change-value', self._schedule_changed_cb)
        self._schedule_scale.connect('format-value', lambda _, v: formatting.formatTime(v))

        self._track_length = 0.0
        self._track_position = 0.0

        self._schedule_length = 0.0
        self._schedule_position = 0.0

        self._track_offset = 0.0

    def set_track_length(self, length):
        self._track_scale.set_range(0, length)
        self._track_length = length

        self._update_track_label()

    def set_track_position(self, position):
        self._track_scale.set_value(position)

        self._update_track_label()

    def set_track_offset(self, offset):
        self._track_offset = offset

    def _update_track_label(self):
        self._track_label.set_text('%s' %
            formatting.formatTime(self._track_length))

    def set_schedule_length(self, length):
        self._schedule_scale.set_range(0, length)
        self._schedule_length = length

        self._update_schedule_label()

    def set_schedule_position(self, position):
        self._schedule_scale.set_value(position)

        self._update_schedule_label()

    def _update_schedule_label(self):
        self._schedule_label.set_text('%s' % 
            formatting.formatTime(self._schedule_length))

    def _track_changed_cb(self, scale, scroll, value):
        self._track_position = scale.get_value()
        self._update_track_label()
        self.debug('seeked track to %r, schedule to %r',
            self._track_position, self._track_position + self._track_offset)
        self.emit('seeked-schedule', self._track_position + self._track_offset)

    def _schedule_changed_cb(self, scale, scroll, value):
        self._schedule_position = scale.get_value()
        self._update_schedule_label()
        self.debug('seeked schedule to %r',
            self._schedule_position)
        self.emit('seeked-schedule', self._schedule_position)

gobject.type_register(SeekUI)

def main():
    window = gtk.Window()

    s = SeekUI()

    s.set_schedule_length(3600)
    s.set_schedule_position(10)

    s.set_track_length(160)
    s.set_track_position(10)
    s.set_track_offset(300)


    def seeked_cb(seekui, position):
        print 'Seeked to', position

    s.connect('seeked-track', seeked_cb)
    s.connect('seeked-schedule', seeked_cb)

    window.add(s)
    window.connect('destroy', lambda _: gtk.main_quit())

    window.set_default_size(600, 200)
    window.show_all()

if __name__ == "__main__":
    main()
    gtk.main()

