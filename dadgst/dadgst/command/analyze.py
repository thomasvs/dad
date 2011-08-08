# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding GStreamer-based functionality to dad command

import os

from dad import idad
from dad.audio import common
from dad.common import logcommand

from dadgst.task import level, fingerprint

from dadgst.extern.task import task

class ChromaPrint(logcommand.LogCommand):
    description = """Calculates acoustid chromaprint fingerprint."""

    def do(self, args):
        import gobject
        gobject.threads_init()

        runner = task.SyncRunner()

        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue

            t = fingerprint.ChromaPrintTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))
            self.stdout.write('chromaprint:\n%s\n' % t.fingerprint)


class Level(logcommand.LogCommand):
    description = """Shows levels for audio files."""

    def do(self, args):
        import pygst
        pygst.require('0.10')
        import gobject
        gobject.threads_init()
        import gst

        from dadgst.task import level

        runner = task.SyncRunner()

        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue

            t = level.LevellerTask(path)
            runner.run(t)

            if t.done:
                self.stdout.write('Successfully analyzed file %s.\n' %
                    path.encode('utf-8'))
                mixes = t.get_track_mixes()
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
            else:
                self.stderr.write('Could not level %s\n' %
                    path.encode('utf-8'))

            t.clean()

        
class Metadata(logcommand.LogCommand):
    description = """Shows metadata for audio files."""

    def do(self, args):
        import gobject
        gobject.threads_init()

        import gst

        runner = task.SyncRunner()

        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue

            t = level.TagReadTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))
            for name, tag in [
                ('Artist', gst.TAG_ARTIST),
                ('Title', gst.TAG_TITLE),
                ('Album', gst.TAG_ALBUM),
            ]:
                if tag in t.taglist:
                    self.stdout.write('- %s: %s\n' % (name, t.taglist[tag]))

class TRM(logcommand.LogCommand):
    description = """Calculates TRM fingerprint."""

    def do(self, args):
        import gobject
        gobject.threads_init()

        runner = task.SyncRunner()

        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue

            t = fingerprint.TRMTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))
            self.stdout.write('TRM %s\n' % t.trm)


class Analyze(logcommand.LogCommand):
    description = """Analyzes audio files."""

    subCommandClasses = [ ChromaPrint, Level, Metadata, TRM, ]
