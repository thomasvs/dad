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

import gobject
import gst

from gst.extend import sources, utils, pygobject

from dad.audio import level

class Leveller(gst.Pipeline):
    """
    I am a pipeline that calculates RMS/decay/peak values for each channel.

    I will signal 'done' when I'm done scanning the file, with return value
    EOS, ERROR, UNKNOWN_TYPE, or WRONG_TYPE from gst.extend.sources

    If I signaled EOS, then the arrays of RMS/decay/peak values can be
    retrieved from me.

    @ivar  rmsdB:   list of (time, tuple of rms values per channel)
    @type  rmsdB:   list of (long, [tuple of float])
    @ivar  peakdB:  list of (time, tuple of peak values per channel)
    @type  peakdB:  list of (long, [tuple of float])
    @ivar  decaydB: list of (time, tuple of decay values per channel)
    @type  decaydB: list of (long, [tuple of float])
    """

    pygobject.gsignal('done', str)

    def __init__(self, filename):
        """
        @param filename: relative or absolute filename
        @type  filename: str
        """
        gst.Pipeline.__init__(self)
        self._channels = None

        self._filename = filename

        self._source = sources.AudioSource(filename)
        self._source.connect('done', self._source_done_cb)

        self._level = gst.element_factory_make("level")

        self._fakesink = gst.element_factory_make("fakesink")

        self.add(self._source, self._level, self._fakesink)
        self._source.connect("pad-added", self._source_pad_added_cb)
        self._level.link(self._fakesink)

        # will be set when done

        self.rmsdBs = [] # list of Level, one per channel
        self.peakdB = level.Level(scale=level.SCALE_DECIBEL)
        self.decaydB = level.Level(scale=level.SCALE_DECIBEL)

    ### public API
    def get_channels(self):
        """
        Return the number of channels in the source.
        """
        return self._channels

    def get_rms(self, channel=None):
        """
        Get the list of RMS values for the given channel, from 0.0 to 1.0
        If no channel specified, take RMS over all channels.

        @param channel: channel number to get RMS values for, starting from 0
        @type  channel: int or None

        @rtype:   L{level.Level}
        """
        if channel is not None:
            return self.rmsdBs[channel]

        rmss = [l.convert(level.SCALE_RAW) for l in self.rmsdBs]

        ret = level.Level(scale=level.SCALE_RAW)

        # to take RMS over multiple channels, we need to root and average the
        # sum of squares for each channel
        def _rms_list(values):
            v = math.sqrt(sum([v ** 2 for v in values]) / len(values))
            return v

        for i, _ in enumerate(rmss[0]):
            endtime = rmss[0][i][0]
            values = [l[i][1] for l in rmss]
            ret.append((endtime, _rms_list(values)))

        return ret


    def get_rms_dB(self, channel=None):
        """
        Get the list of RMS values for the given channel, in dB.
        If no channel specified, take RMS over all channels.

        @param channel: channel number to get rms values for, starting from 0
        @type  channel: int or None

        @rtype:   L{level.Level}
        """
        if channel is not None:
            return self.rmsdBs[channel]

        l = self.get_rms()
        return l.convert(scale=level.SCALE_DECIBEL)

    def get_peak(self, channel=None):
        """
        Get the list of peak values for the given channel.
        If no channel specified, take peak over all channels.

        @param channel: channel number to get peak values for, starting from 0
        @type  channel: int or None
        """
        return self.get_peak_dB(channel).convert(level.SCALE_RAW)

    def get_peak_dB(self, channel=None):
        """
        Get the list of peak values for the given channel, in dB.
        If no channel specified, take peak over all channels.

        @param channel: channel number to get peak values for, starting from 0
        @type  channel: int or None
        """
        if channel is not None:
            return self.peakdBs[channel]

        peak = level.Level(scale=level.SCALE_DECIBEL)
        for i, (endtime, v) in enumerate(self.peakdBs[0]):
            peak.append((endtime, max([l[i][1] for l in self.peakdBs])))

        return peak

    ### gst.Bin::handle_message override

    def do_handle_message(self, message):
        self.log("got message %r" % message)
        if message.type == gst.MESSAGE_ELEMENT and message.src == self._level:
            s = message.structure
            
            # initialize if this is the first message
            if not self._channels:
                self._channels = len(s["rms"])
                self.rmsdBs = [level.Level(scale=level.SCALE_DECIBEL)
                    for c in range(self._channels)]
                self.peakdBs = [level.Level(scale=level.SCALE_DECIBEL)
                    for c in range(self._channels)]
                self.decaydBs = [level.Level(scale=level.SCALE_DECIBEL)
                    for c in range(self._channels)]

            endtime = s["endtime"]
            for channel, value in enumerate(tuple(s["rms"])):
                self.rmsdBs[channel].append((endtime, value))
            for channel, value in enumerate(tuple(s["peak"])):
                self.peakdBs[channel].append((endtime, value))
            for channel, value in enumerate(tuple(s["decay"])):
                self.decaydBs[channel].append((endtime, value))
        elif message.type == gst.MESSAGE_EOS:
            # whole pipeline eos'd, so we're done
            self.emit('done', sources.EOS)
        # chain up 
        gst.Pipeline.do_handle_message(self, message)

    ### source callbacks

    def _source_pad_added_cb(self, source, pad):
        self._source.link(self._level)

    def _source_done_cb(self, source, reason):
        gst.debug("done, reason %s" % reason)
        # we ignore eos as a reason here because we wait for pipeline EOS
        # in do_handle_message
        if reason == sources.EOS:
            return

        # any other reason gets passed through
        self.emit('done', reason)

    ### public methods

    def start(self):
        gst.debug("Setting to PLAYING")
        self.set_state(gst.STATE_PLAYING)
        gst.debug("Set to PLAYING")

    # FIXME: we might want to do this ourselves automatically ?
    def stop(self):
        """
        Stop the leveller.
        Call this after the leveller emitted 'done'.
        Calls clean.
        """
        gst.debug("Setting to NULL")
        self.set_state(gst.STATE_NULL)
        gst.debug("Set to NULL")
        utils.gc_collect('Leveller.stop()')

    def clean(self):
        """
        Clean up the leveller.
        After calling this, the object cannot be used anymore.
        """
        # clean ourselves up completely
        self.stop()

        # let's be ghetto and clean out our bin manually
        self.remove(self._source)
        self.remove(self._level)
        self.remove(self._fakesink)
        gst.debug("Emptied myself")
        self._source.clean()
        utils.gc_collect('Leveller.clean() cleaned up source')
        self._source = None
        self._fakesink = None
        self._level = None
        utils.gc_collect('Leveller.clean() done')

gobject.type_register(Leveller)

if __name__ == "__main__":
    # this call is always necessary if we're going to have callbacks from
    # threads
    gobject.threads_init()

    main = gobject.MainLoop()

    try:
        leveller = Leveller(sys.argv[1])
    except IndexError:
        sys.stderr.write("Please give a file to calculate level of\n")
        sys.exit(1)

    bus = leveller.get_bus()
    bus.add_signal_watch()
    done = False
    success = False

    leveller.start()
    
    while not done:
        # this call blocks until there is a message
        message = bus.poll(gst.MESSAGE_ANY, gst.SECOND)
        if message:
            gst.debug("got message from poll: %s/%r" % (message.type, message))
        else:
            gst.debug("got NOTHING from poll")
        if message:
            if message.type == gst.MESSAGE_EOS:
                done = True
                success = True
            elif message.type == gst.MESSAGE_ERROR:
                done = True

    leveller.stop()
    leveller.clean()

    if success:
        print 'Successfully analyzed file.'
        if len(sys.argv) > 2:
            path = sys.argv[2]
            handle = open(path, 'w')
            import pickle
            pickle.dump(leveller.get_rms_dB(), handle, 2)
            handle.close()
            print 'Dumped RMS dB pickle to %s' % path
    gst.debug('deleting leveller, verify objects are freed')
    utils.gc_collect('quit main loop')
    del leveller
    utils.gc_collect('deleted leveller')
    gst.debug('stopping forever')
