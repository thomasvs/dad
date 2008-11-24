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

import sys

import pickle

import gobject
import gst

from gst.extend import utils

from dad.gstreamer import leveller

def main():
    # this call is always necessary if we're going to have callbacks from
    # threads
    gobject.threads_init()

    main = gobject.MainLoop()

    # load our pickle

    tracks = {} # dict of path -> list of mixdata

    try:
        handle = open(sys.argv[1])
        tracks = pickle.load(handle)
        handle.close()
    except IndexError:
        sys.stderr.write("Please give a pickle file for tracks.\n")
        sys.exit(1)
    except IOError:
        # does not exist yet, so we'll create it when we save
        pass

    for path in sys.argv[2:]:
        if path in tracks.keys():
            print '%r already analyzed, skipping' % path
            continue

        print 'Analyzing file %r' % path
        l = leveller.Leveller(path)
        bus = l.get_bus()
        bus.add_signal_watch()
        done = False
        success = False

        l.start()
        
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

        l.stop()
        l.clean()

        if success:
            print 'Successfully analyzed file %r' % path
            mixdatas = l.get_mixdatas()
            print '%d slices found.' % len(mixdatas)
            for i, m in enumerate(mixdatas):
                print 'slice %d: %s - %s, peak %r dB, RMS %r dB' % (
                    i, gst.TIME_ARGS(m.start), gst.TIME_ARGS(m.end),
                    m.peakdB, m.rmsdB)

            tracks[path] = mixdatas
            handle = open(sys.argv[1], 'wb')
            pickle.dump(tracks, handle, 2)
            handle.close()

        gst.debug('deleting leveller, verify objects are freed')
        utils.gc_collect('quit main loop')
        del l
        utils.gc_collect('deleted leveller')
        gst.debug('stopping forever')

main()
