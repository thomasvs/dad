# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import urllib

from twisted.internet import defer
from twisted.web import client

from dad.common import log
from dad.base import data


CHROMAPRINT_APIKEY = 'pmla1DI5' # for DAD 0.0.0
CHROMAPRINT_URL = 'http://api.acoustid.org/v2/lookup'

class ChromaPrintClient(log.Loggable):

    @defer.inlineCallbacks
    def lookup(self, duration, fingerprint):
        postdata = {
            'client': CHROMAPRINT_APIKEY,
            'meta':   '2',
            'duration': str(duration),
            'fingerprint': fingerprint
        }

        resp = None
        for i in range(0, 3):
            try:
                d = client.getPage(CHROMAPRINT_URL, method='POST',
                    postdata=urllib.urlencode(postdata),
                    headers={'Content-Type':'application/x-www-form-urlencoded'})
                resp = yield d
                # uncomment for a quick debug that you can paste in tests
                # print resp.read()
                break
            except Exception, e:
                self.debug('Failed to open %r',
                    log.getExceptionMessage(e))

        import simplejson

        if not resp:
            self.debug('Failed to look up track with fingerprint %s\n' %
                fingerprint)
            defer.returnValue(None)
            return

        try:
            decoded = simplejson.loads(resp)
        except Exception, e:
                self.debug('Failed to json-decode %r: %r',
                    resp, log.getExceptionMessage(e))
                defer.returnValue(e)
                return

        if decoded['status'] == 'ok':
            results = decoded['results']
            self.debug('Found %d results\n' % len(results))

            for result in results:
                recordings = result.get('recordings', [])
                self.debug('- Found %d recordings.\n' %
                    len(recordings))
                for recording in recordings:
                    self.debug('  - musicbrainz id: %s\n' %
                        recording['id'])
                    self.debug(
                        '  - URL: http://musicbrainz.org/recording/%s\n' %
                            recording['id'])

                    for track in recording.get('tracks', []):
                        for artist in track['artists']:
                            self.debug('    - artist: %s\n' %
                                artist['name'].encode('utf-8'))
                        self.debug('    - title: %s\n' %
                            track['title'].encode('utf-8'))

                        # these all ought to contain the same info,
                        # since it's the same musicbrainz id
                        break

            fp = data.ChromaPrint()
            fp.fromResults(results)
            self.debug('metadata: %r', fp.metadata)
            defer.returnValue(fp, decoded)
        else:
            print 'ERROR:', result
            defer.returnValue(None)
