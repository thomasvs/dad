# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding GStreamer-based functionality to dad command

import os

from dad.audio import common
from dad.common import logcommand

class Level(logcommand.LogCommand):
    description = """Shows levels for audio files."""

    def do(self, args):
        import pygst
        pygst.require('0.10')
        import gobject
        gobject.threads_init()
        import gst

        from dadgst.gstreamer import leveller

        for path in args:
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n', path)
                continue

            level = leveller.Leveller(path)

            success = leveller.run(level)

            if success:
                self.stdout.write('Successfully analyzed file %s.\n' %
                    path)
                mixes = level.get_track_mixes()
                self.stdout.write('%d fragment(s)\n' % len(mixes))

                for i, m in enumerate(mixes):
                    self.stdout.write('- fragment %d: %s - %s\n' % (
                        i, gst.TIME_ARGS(m.start), gst.TIME_ARGS(m.end)))
                    self.stdout.write('  - peak              %02.3f dB (%03.3f %%)\n' % (
                        m.peak, common.decibelToRaw(m.peak) * 100.0))
                    self.stdout.write('  - rms               %r dB\n' % m.rms)
                    self.stdout.write('  - peak rms          %r dB\n' % m.rmsPeak)
                    self.stdout.write('  - 95 percentile rms %r dB\n' % m.rmsPercentile)
                    self.stdout.write('  - weighted rms      %r dB\n' % m.rmsWeighted)
                    start = m.attack.get(m.rmsPeak - 9)
                    end = m.decay.get(m.rmsPeak - 9)
                    self.stdout.write('  - weighted from %s to %s\n' % (
                        gst.TIME_ARGS(start), gst.TIME_ARGS(end)))

            level.clean()

        
class Metadata(logcommand.LogCommand):
    description = """Shows metadata for audio files."""

class Analyze(logcommand.LogCommand):
    description = """Analyzes audio files."""

    subCommandClasses = [ Level, Metadata, ]


# called by main command code before instantiating the class
def plugin(dadCommandClass):
    dadCommandClass.subCommandClasses.append(Analyze)
