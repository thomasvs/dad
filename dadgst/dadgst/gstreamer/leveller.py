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

from gst.extend import sources, utils, pygobject

from dad.audio import level, mixing

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

        # uridecodebin only takes absolute URI's, so we need an abspath
        filename = os.path.abspath(filename)

        if not os.path.exists(filename):
            raise KeyError, "%s does not exist" % filename

        self._filename = filename


        self._source = gst.element_factory_make('uridecodebin')
        # FIXME: we probably need to encode the uri better
        self._source.props.uri = 'file://' + urllib.quote(filename)
        gst.debug('__init__: source refcount: %d' % self._source.__grefcount__)

        self._level = gst.element_factory_make("level")
        self._level.set_property('interval', gst.SECOND / 20) # 50 ms

        self._fakesink = gst.element_factory_make("fakesink")

        self.add(self._source, self._level, self._fakesink)
        gst.debug('__init__ add: source refcount: %d' % self._source.__grefcount__)
        self._source.connect("pad-added", self._source_pad_added_cb)
        gst.debug('__init__ connect: source refcount: %d' % self._source.__grefcount__)
        self._level.link(self._fakesink)

        # will be set when done

        self.rmsdBs = [] # list of Level, one per channel
        self.peakdB = level.Level(scale=level.SCALE_DECIBEL)
        self.decaydB = level.Level(scale=level.SCALE_DECIBEL)

        gst.debug('__init__ end: source refcount: %d' % self._source.__grefcount__)

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

        rmss = [l.convert(scale=level.SCALE_RAW) for l in self.rmsdBs]

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

        @returns: the peak level graph in dB
        @rtype:   L{level.Level}
        """
        if channel is not None:
            return self.peakdBs[channel]

        peak = level.Level(scale=level.SCALE_DECIBEL)

        for i, (endtime, v) in enumerate(self.peakdBs[0]):
            maxdB = max([l[i][1] for l in self.peakdBs])
            if maxdB > 0.0:
                gst.warning('maxdB higher than unity: %r dB' % maxdB)
            peak.append((endtime, maxdB))

        return peak

    def get_track_mixes(self):
        """
        Get track mixes for all slices in this track.

        @returns: list of track mixes for each slice
        @rtype:   list of L{dad.audio.mixing.TrackMix}
        """
        ret = []
        
        rms = self.get_rms_dB()
        peak = self.get_peak_dB()
        slices = rms.slice()

        # If there are no slices, then the track is silent.
        # In that case, return the full track.
        if not slices:
            slices = [rms, ]

        for i, s in enumerate(slices):
            m = mixing.fromLevels(s, peak.trim(start=s.start(), end=s.end()))
            if i == 0:
                m.name = self._filename
            else:
                m.name = "slice %d of %s" % (i + 1, self._filename)
            ret.append(m)

        return ret

    ### gst.Pipeline::handle_message override

    def do_handle_message(self, message):
        self.log("got message %r" % message)
        if message.type == gst.MESSAGE_ELEMENT and message.src == self._level:
            s = message.structure
            
            # initialize if this is the first message
            if not self._channels:
                self._channels = len(s["rms"])
                self.debug("got %d channels" % self._channels)
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
            self.debug("EOS, done")
            # whole pipeline eos'd, so we're done
            self.emit('done', sources.EOS)

        # chain up 
        gst.Pipeline.do_handle_message(self, message)
        self.log("handled message %r" % message)

    ### source callbacks

    def _source_pad_added_cb(self, source, pad):
        self._source.link(self._level)

    # FIXME: removed now
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
        self.debug("Setting to PLAYING")
        self.set_state(gst.STATE_PLAYING)
        self.debug("Set to PLAYING, refcount now %d" % self.__grefcount__)

    # FIXME: we might want to do this ourselves automatically ?
    def stop(self):
        """
        Stop the leveller.
        Call this after the leveller emitted 'done'.
        Calls clean.
        """
        gst.debug("Setting to NULL")
        self.set_state(gst.STATE_NULL)
        self.debug("Set to NULL, refcount now %d" % self.__grefcount__)
        utils.gc_collect('Leveller.stop()')

    def clean(self):
        """
        Clean up the leveller.
        After calling this, the object cannot be used anymore.
        """
        # clean ourselves up completely
        self.stop()

        self.remove(self._source)
        self.remove(self._level)
        self.remove(self._fakesink)
        gst.debug("Emptied myself")
        utils.gc_collect('Leveller.clean() cleaned up source')
        self.debug("source refcount: %d" % self._source.__grefcount__)

        self._source = None
        self._fakesink = None
        self._level = None

        self.rmsdBs = None
        self.peakdBs = None
        self.decaydBs = None

        utils.gc_collect('Leveller.clean() done')
        self.debug("clean done, refcount now %d" % self.__grefcount__)

gobject.type_register(Leveller)

def run(leveller):

    gst.debug('leveller refcount on creation: %d' % leveller.__grefcount__)

    bus = leveller.get_bus()
    bus.add_signal_watch()
    done = False
    success = False

    gst.debug('leveller refcount before start: %d' % leveller.__grefcount__)
    utils.gc_collect('before start')
    leveller.start()
    gst.debug('leveller refcount after start: %d' % leveller.__grefcount__)
    utils.gc_collect('after start')
    
    while not done:
        # this call blocks until there is a message
        message = bus.poll(gst.MESSAGE_ANY, gst.SECOND)
        if message:
            gst.log("got message from poll: %s/%r" % (message.type, message))
        else:
            gst.log("got NOTHING from poll")
        if message:
            if message.type == gst.MESSAGE_EOS:
                done = True
                success = True
            elif message.type == gst.MESSAGE_ERROR:
                done = True

        # message, if set, holds a ref to leveller, so we delete it here
        # to assure cleanup of leveller when we del it
        m = repr(message)
        del message
        utils.gc_collect('deleted message %s' % m)


    bus.remove_signal_watch()
    del bus
    utils.gc_collect('deleted bus')
    leveller.stop()


    return success

if __name__ == "__main__":
    # this call is always necessary if we're going to have callbacks from
    # threads
    gobject.threads_init()

    #main = gobject.MainLoop()

    try:
        leveller = Leveller(sys.argv[1])
    except IndexError:
        sys.stderr.write("Please give a file to calculate level of\n")
        sys.exit(1)

    success = run(leveller)

    if success:
        print 'Successfully analyzed file.'
        if len(sys.argv) > 2:
            path = sys.argv[2]
            handle = open(path, 'w')
            import pickle
            rms = leveller.get_rms_dB()
            pickle.dump(rms, handle, pickle.HIGHEST_PROTOCOL)
            handle.close()
            print 'Dumped RMS dB pickle to %s' % path

    leveller.clean()

    assert leveller.__grefcount__ == 1, "There is a leak in leveller's refcount"
    gst.debug('deleting leveller, verify objects are freed')
    del leveller
    utils.gc_collect('deleted leveller')
    utils.gc_collect('deleted leveller')
    utils.gc_collect('deleted leveller')

    # some more cleanup to help valgrind
    gst.debug('stopping forever')
