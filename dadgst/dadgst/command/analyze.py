# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding GStreamer-based functionality to dad command

import os

from dad.audio import common
from dad.common import log, logcommand
from dad.base import data

from dadgst.task import level, fingerprint

from dad.extern.task import task

CHROMAPRINT_APIKEY = 'pmla1DI5' # for DAD 0.0.0

def filterFiles(outer, args):
    paths = []

    for path in args:
        path = path.decode('utf-8')

        if not os.path.exists(path):
            outer.stderr.write('Could not find %s.\n' % path.encode('utf-8'))
            continue

        if os.path.isdir(path):
            outer.stderr.write('%s is a directory.\n' % path.encode('utf-8'))
            continue

        paths.append(path)

    return paths

 
class ChromaPrint(logcommand.LogCommand):
    description = """Calculates acoustid chromaprint fingerprint."""

    def addOptions(self):
        self.parser.add_option('-L', '--no-lookup',
            action="store_true", dest="no_lookup",
            help="don't look up the fingerprint, only show it")

    def do(self, args):
        import gobject
        gobject.threads_init()

        runner = task.SyncRunner()

        for path in filterFiles(self, args):
            t = fingerprint.ChromaPrintTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))
            if self.options.no_lookup:
                self.stdout.write('chromaprint:\n%s\n' % t.fingerprint)
                continue

            # now look it up
            # FIXME: translate to twisted-y code
            lookup = {
                'client': CHROMAPRINT_APIKEY,
                'meta':   '2',
                'duration': str(t.duration),
                'fingerprint': t.fingerprint
            }
            import urllib
            import urllib2

            url = 'http://api.acoustid.org/v2/lookup'
            resp = None
            for i in range(0, 3):
                try:
                    resp = urllib2.urlopen(url, urllib.urlencode(lookup))
                    # uncomment for a quick debug that you can paste in tests
                    # print resp.read()
                    break
                except Exception, e:
                    self.debug('Failed to open %r',
                        log.getExceptionMessage(e))
                    

            import simplejson

            if not resp:
                self.debug('Failed to look up %r', lookup)
                continue

            try:
                decoded = simplejson.load(resp)
            except Exception, e:
                    self.debug('Failed to json-decode %r', resp)
                    continue

            if decoded['status'] == 'ok':
                results = decoded['results']
                self.stdout.write('Found %d results\n' % len(results))

                for result in results:
                    recordings = result.get('recordings', [])
                    self.stdout.write('- Found %d recordings.\n' %
                        len(recordings))
                    for recording in recordings:
                        self.stdout.write('  - musicbrainz id: %s\n' %
                            recording['id'])
                        self.stdout.write(
                            '  - URL: http://musicbrainz.org/recording/%s\n' %
                                recording['id'])

                        for track in recording.get('tracks', []):
                            for artist in track['artists']:
                                self.stdout.write('    - artist: %s\n' %
                                    artist['name'].encode('utf-8'))
                            self.stdout.write('    - title: %s\n' %
                                track['title'].encode('utf-8'))

                            # these all ought to contain the same info,
                            # since it's the same musicbrainz id
                            break

                fp = data.ChromaPrint()
                fp.fromResults(results)
                self.stdout.write('%r\n' % fp.metadata)
            else:
                print 'ERROR:', result


class OFAPrint(logcommand.LogCommand):

    description = """Calculates OFA/MusicIP fingerprint."""

    def do(self, args):
        import gobject
        gobject.threads_init()

        runner = task.SyncRunner()

        for path in filterFiles(self, args):
            t = fingerprint.OFAPrintTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))
            if self.options.no_lookup:
                self.stdout.write('ofa print:\n%s\n' % t.fingerprint)
                continue


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

        for path in filterFiles(self, args):

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

        for path in filterFiles(self, args):

            t = level.TagReadTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))

            keys = []

            for name, tag in [
                ('Artist', gst.TAG_ARTIST),
                ('Title', gst.TAG_TITLE),
                ('Album', gst.TAG_ALBUM),
            ]:
                if tag in t.taglist:
                    self.stdout.write('- %s: %r\n' % (name, t.taglist[tag]))

            for tag in t.taglist.keys():
                self.stdout.write('- %s: %r\n' % (tag, t.taglist[tag]))


class TRM(logcommand.LogCommand):
    description = """Calculates TRM fingerprint."""

    def do(self, args):
        import gobject
        gobject.threads_init()

        runner = task.SyncRunner()

        for path in filterFiles(self, args):

            t = fingerprint.TRMTask(path)
            runner.run(t)

            self.stdout.write('%s:\n' % path.encode('utf-8'))
            self.stdout.write('TRM %s\n' % t.trm)


class Analyze(logcommand.LogCommand):
    description = """Analyzes audio files."""

    subCommandClasses = [ ChromaPrint, OFAPrint, Level, Metadata, TRM, ]
