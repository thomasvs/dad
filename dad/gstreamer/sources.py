# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# DAD - Digital Audio Database
# Copyright (C) 2008 Thomas Vander Stichele <thomas at apestaart dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# only require pygst when we're executed instead of imported
if __name__ == '__main__':
    import pygst
    pygst.require('0.10')

import os
import sys
import math
import urllib

import gobject
import gst


class AudioSource(gst.Bin):
    """
    I am an audio source that decodes a path to raw audio.
    """
    def __init__(self, path):

        gst.Bin.__init__(self)

        caps = gst.caps_from_string('audio/x-raw-int;audio/x-raw-float')

        self._source = gst.element_factory_make('uridecodebin', 'source-decodebin')
        self._source.props.uri = 'file://' + urllib.quote(path)

        self._convert = gst.element_factory_make('audioconvert', 'source-convert')
        self._volume = gst.element_factory_make('volume', 'source-volume')
        self.add(self._source, self._convert, self._volume)
        self._convert.link(self._volume)

        self._source.connect('pad-added', self._source_pad_added_cb)
        self._source.connect('pad-removed', self._source_pad_removed_cb)

        ghost = gst.GhostPad("src", self._volume.get_pad("src"))
        ghost.set_active(True)
        self.add_pad(ghost)


    def _source_pad_added_cb(self, source, pad):
        print 'source pad added', source, pad
        print 'caps', pad.get_caps()
        pad.link(self._convert.get_pad("sink"))

    def _source_pad_removed_cb(self, source, pad):
        print 'source pad removed', source, pad
        # workaround for gstreamer bug as taken from pitivi's source.py
        # gpad = self._volume.get_pad("src")
        gpad = self.get_pad("src")
        target = gpad.get_target()
        peer = target.get_peer()
        target.unlink(peer)
        # self.remove_pad(self._volume.get_pad("src"))
        self.remove_pad(gpad)

    def set_volume(self, volume):
        self._volume.props.volume = volume
