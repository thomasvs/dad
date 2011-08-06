# -*- Mode: Python; test-case-name: dadgst.task.fingerprint -*-
# vi:si:et:sw=4:sts=4:ts=4

# DAD - Digital Audio Database

# Copyright (C) 2011 Thomas Vander Stichele

# This file is part of DAD.
# 
# morituri is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# morituri is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with morituri.  If not, see <http://www.gnu.org/licenses/>.

import sys
import math
import urllib

import gobject

from dad.audio import level, mixing

from dad.extern.log import log
from dadgst.extern.task import gstreamer


# FIXME: copied from morituri.common.checksum, improve and put back

TRM_DURATION = 26086167800L # experimentally deduced, in ns

class TRMTask(log.Loggable, gstreamer.GstPipelineTask):
    """
    I calculate a MusicBrainz TRM fingerprint.

    @ivar trm: the resulting trm
    """

    trm = None
    description = 'Calculating TRM fingerprint'

    def __init__(self, path):
        assert type(path) is unicode, "path %r is not unicode" % path

        self._path = path
        self._trm = None

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin ! audioconvert ! audio/x-raw-int !
            trm name=trm !
            appsink name=sink sync=False emit-signals=True''' % (
                gstreamer.quoteParse(self._path).encode('utf-8'), )

    ### base class implementations

    def parsed(self):
        sink = self.pipeline.get_by_name('sink')
        sink.connect('new-buffer', self._new_buffer_cb)

    def paused(self):
        self.gst.debug('query duration')

        self._length, qformat = self.pipeline.query_duration(self.gst.FORMAT_TIME)
        self.gst.debug('total length: %r' % self._length)
        self.gst.debug('scheduling setting to play')
        # since set_state returns non-False, adding it as timeout_add
        # will repeatedly call it, and block the main loop; so
        #   gobject.timeout_add(0L, self.pipeline.set_state, gst.STATE_PLAYING)
        # would not work.


    # FIXME: can't move this to base class because it triggers too soon
    # in the case of checksum
    def bus_eos_cb(self, bus, message):
        self.gst.debug('eos, scheduling stop')
        self.schedule(0, self.stop)


    def bus_tag_cb(self, bus, message):
        taglist = message.parse_tag()
        if 'musicbrainz-trmid' in taglist.keys():
            self._trm = taglist['musicbrainz-trmid']

    def _new_buffer_cb(self, sink):
        # this is just for counting progress
        buf = sink.emit('pull-buffer')
        position = buf.timestamp
        self._position = position
        if buf.duration != self.gst.CLOCK_TIME_NONE:
            position += buf.duration
        self.setProgress(float(position) / min(TRM_DURATION, self._length))

    def bus_tag_cb(self, bus, message):
        self.log("got message %r" % message)
        taglist = message.parse_tag()
        if 'musicbrainz-trmid' not in taglist:
            return
        self._trm = taglist['musicbrainz-trmid']
        self.debug('got TRM, scheduling stop')

        self.schedule(0, self.stop)

    def bus_eos_cb(self, bus, message):
        self.debug('eos, scheduling stop')
        self.done = True

        self.schedule(0, self.stop)

    def stopped(self):
        self.trm = self._trm
