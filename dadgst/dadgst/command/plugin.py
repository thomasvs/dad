# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding GStreamer-based functionality to dad command

import os

from dad.common import logcommand

class Level(logcommand.LogCommand):
    description = """Shows levels for audio files."""

    def do(self, args):
        import pygst
        pygst.require('0.10')
        import gobject
        gobject.threads_init()

        from dadgst.gstreamer import leveller

        for path in args:
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n', path)
                continue

            level = leveller.Leveller(path)

            success = leveller.run(level)

            if success:
                print 'Successfully analyzed file.'
                rms = level.get_rms_dB()
                print rms

                mixes = level.get_track_mixes()
                print '%d slices' % len(mixes)

            level.clean()

        
class Metadata(logcommand.LogCommand):
    description = """Shows metadata for audio files."""

class Analyze(logcommand.LogCommand):
    description = """Analyzes audio files."""

    subCommandClasses = [ Level, Metadata, ]


# called by main command code before instantiating the class
def plugin(dadCommandClass):
    dadCommandClass.subCommandClasses.append(Analyze)
