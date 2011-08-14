# -*- Mode: Python; test-case-name: dadgst.task.level -*-
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

class GstLogPipelineTask(log.Loggable, gstreamer.GstPipelineTask):

    def error(self, message, *args):
        log.Loggable.doLog(self, log.ERROR, -2, message, *args)

    def warning(self, message, *args):
        log.Loggable.doLog(self, log.WARNING, -2, message, *args)

    def info(self, message, *args):
        log.Loggable.doLog(self, log.INFO, -2, message, *args)

    def debug(self, message, *args):
        log.Loggable.doLog(self, log.DEBUG, -2, message, *args)

    def log(self, message, *args):
        log.Loggable.doLog(self, log.LOG, -2, message, *args)


class LevellerTask(GstLogPipelineTask):
    """
    I am a task that calculates levels on an input file.
    """

    logCategory = 'LevellerTask'

    description = 'Calculating levels'

    done = None

    _duration = None
    _channels = None

    def __init__(self, inpath):
        assert type(inpath) is unicode, "inpath %r is not unicode" % inpath

        self._inpath = inpath

    ### source callbacks

    def _source_pad_added_cb(self, source, pad):
        self._source.link(self._level)

    ### base class implementations

    def getPipeline(self):
        self.pipeline = self.gst.Pipeline()

        self._source = self.gst.element_factory_make('uridecodebin')
        # FIXME: we probably need to encode the uri better
        self._source.props.uri = 'file://' + urllib.quote(self._inpath.encode('utf-8'))
        self.debug('__init__: source refcount: %d' % self._source.__grefcount__)

        self._level = self.gst.element_factory_make("level")
        self._level.set_property('interval', self.gst.SECOND / 20) # 50 ms

        self._fakesink = self.gst.element_factory_make("fakesink")

        self.pipeline.add(self._source, self._level, self._fakesink)
        self.debug('__init__ add: source refcount: %d' % self._source.__grefcount__)
        self._source.connect("pad-added", self._source_pad_added_cb)
        self.debug('__init__ connect: source refcount: %d' % self._source.__grefcount__)
        self._level.link(self._fakesink)

        # will be set when done

        self.rmsdBs = [] # list of Level, one per channel
        self.peakdB = level.Level(scale=level.SCALE_DECIBEL)
        self.decaydB = level.Level(scale=level.SCALE_DECIBEL)

        self.debug('__init__ end: source refcount: %d' % self._source.__grefcount__)

    def parsed(self):
        self.bus.connect('sync-message::element', self._message_element_cb)
        
    def paused(self):
        # get duration
        self.debug('query duration')
        try:
            duration, qformat = self._level.query_duration(self.gst.FORMAT_TIME)
        except self.gst.QueryError, e:
            self.setException(e)
            # schedule it, otherwise runner can get set to None before
            # we're done starting
            self.schedule(0, self.stop)
            return
        self.debug('queried duration, %r', duration)


        # wavparse 0.10.14 returns in bytes
        if qformat == self.gst.FORMAT_BYTES:
            self.debug('query returned in BYTES format')
            duration /= 4
        self.debug('total duration: %r', duration)
        self._duration = duration


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

        @returns: the peak level graph
        @rtype:   L{level.Level}
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
                self.gst.warning('maxdB higher than unity: %r dB' % maxdB)
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
                m.name = self._inpath
            else:
                m.name = "slice %d of %s" % (i + 1, self._inpath)
            ret.append(m)

        return ret

    def clean(self):
        """
        Clean up the leveller.
        After calling this, the object cannot be used anymore.
        """
        self.pipeline.remove(self._source)
        self.pipeline.remove(self._level)
        self.pipeline.remove(self._fakesink)
        self.debug("Emptied myself")

        from gst.extend import utils
        utils.gc_collect('Leveller.clean() cleaned up source')
        self.debug("source refcount: %d" % self._source.__grefcount__)

        self._source = None
        self._fakesink = None
        self._level = None

        self.rmsdBs = None
        self.peakdBs = None
        self.decaydBs = None

        utils.gc_collect('Leveller.clean() done')
        self.debug("clean done, refcount now %d" % self.pipeline.__grefcount__)

    def _message_element_cb(self, bus, message):
        self.log("got message %r" % message)
        if message.src == self._level:
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
        # FIXME: works around a bug on F-15 where buffer probes don't seem
        # to get triggered to update progress
        if self._duration is not None:
            self.schedule(0, self.setProgress,
                float(s['stream-time'] + s['duration']) / self._duration)

    def bus_eos_cb(self, bus, message):
        self.debug('eos, scheduling stop')
        self.done = True

        self.schedule(0, self.stop)

    def stopped(self):
        return
        if self._peakdB is not None:
            self.debug('peakdB %r', self._peakdB)
            self.peak = math.sqrt(math.pow(10, self._peakdB / 10.0))
        else:
            self.warning('No peak found, something went wrong!')

class TagReadTask(GstLogPipelineTask):
    """
    I am a task that reads tags.

    @ivar  taglist: the tag list read from the file.
    @type  taglist: L{gst.TagList}
    """

    logCategory = 'TagReadTask'

    description = 'Reading tags'

    taglist = None

    def __init__(self, path):
        """
        """
        assert type(path) is unicode, "path %r is not unicode" % path
        
        self._path = path

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin name=decoder !
            fakesink''' % (
                gstreamer.quoteParse(self._path).encode('utf-8'))

    def bus_eos_cb(self, bus, message):
        self.debug('eos, schedule stop()')
        self.schedule(0, self.stop)

    def bus_tag_cb(self, bus, message):
        taglist = message.parse_tag()
        # FIXME: merge tags ?

        # as soon as we have at least ARTIST, we consider we're done
        if self.gst.TAG_ARTIST in taglist:
            self.debug('got a taglist with artist in it, schedule stop()')
            self.taglist = taglist
            # FIXME: stop doesn't actually wait for pipeline to go to
            # paused, so messages may still come from a thread as
            # we're throwing things away
            self.schedule(0, self.stop)

    # FIXME: possibly add a done attribute to base class to signal that
    # the task has reached its objective ?
    def paused(self):
        if self.taglist:
            self.debug('Got taglist in PAUSED, done')
            return True

        return False

class StreamInfoTask(GstLogPipelineTask):
    """
    I am a task that reads streaminfo.

    @ivar  samplerate: samplerate
    @type  length:     length in samples
    """

    description = 'Reading stream info'

    samplerate = None
    length = None

    def __init__(self, path):
        """
        """
        assert type(path) is unicode, "path %r is not unicode" % path
        
        self._path = path

    def getPipelineDesc(self):
        return '''
            filesrc location="%s" !
            decodebin name=decoder !
            fakesink''' % (
                gstreamer.quoteParse(self._path).encode('utf-8'))

    def paused(self):
        # get duration
        self.debug('query duration')
        try:
            duration, qformat = self._level.query_duration(self.gst.FORMAT_DEFAULT)
        except self.gst.QueryError, e:
            self.setException(e)
            # schedule it, otherwise runner can get set to None before
            # we're done starting
            self.schedule(0, self.stop)
            return

        # wavparse 0.10.14 returns in bytes
        if qformat == self.gst.FORMAT_BYTES:
            self.debug('query returned in BYTES format')
            duration /= 4
        self.debug('total duration: %r', duration)
        self.length = duration


    def bus_eos_cb(self, bus, message):
        self.debug('eos, scheduling stop')
        self.schedule(0, self.stop)

    def bus_tag_cb(self, bus, message):
        taglist = message.parse_tag()
        # FIXME: merge tags ?

        # as soon as we have at least ARTIST, we consider we're done
        if self.gst.TAG_ARTIST in taglist:
            self.taglist = taglist
            # FIXME: stop doesn't actually wait for pipeline to go to
            # paused, so messages may still come from a thread as
            # we're throwing things away
            self.schedule(0, self.stop)
