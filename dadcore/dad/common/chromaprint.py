# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import datetime
import urllib

from twisted.internet import defer

from dad.common import log
from dad.model import track


CHROMAPRINT_APIKEY = 'pmla1DI5' # for DAD 0.0.0
CHROMAPRINT_URL = 'http://api.acoustid.org/v2/lookup'

class ChromaPrintClient(log.Loggable):

    @defer.inlineCallbacks
    def lookup(self, chromaprint):
        postdata = {
            'client': CHROMAPRINT_APIKEY,
            'meta':   '2',
            'duration': str(chromaprint.duration),
            'fingerprint': chromaprint.chromaprint
        }

        resp = None
        from twisted.web import client
        for i in range(0, 3):
            try:
                d = client.getPage(CHROMAPRINT_URL, method='POST',
                    postdata=urllib.urlencode(postdata),
                    headers={'Content-Type':'application/x-www-form-urlencoded'})
                resp = yield d
                # uncomment for a quick debug that you can paste in tests
                # print resp
                break
            except Exception, e:
                self.debug('Failed to open %r',
                    log.getExceptionMessage(e))

        import simplejson

        if not resp:
            self.debug('Failed to look up track with fingerprint %s\n' %
                chromaprint.chromaprint)
            defer.returnValue(None)
            return

        self.log('JSON response: %r', resp)

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

                    for t in recording.get('tracks', []):
                        for artist in t['artists']:
                            self.debug('    - artist: %s\n' %
                                artist['name'].encode('utf-8'))
                        self.debug('    - title: %s\n' %
                            t['title'].encode('utf-8'))

                        # these all ought to contain the same info,
                        # since it's the same musicbrainz id
                        break

            if not results:
                defer.returnValue(None)
                return

            # FIXME: do we want to add to the original object ? Is that dirty?
            cp = track.ChromaPrintModel()
            # FIXME: when getting it back from couchdb, this should be
            # converted to int instead
            cp.duration = int(chromaprint.duration)
            cp.lookedup = datetime.datetime.now()
            cp.fromResults(results)
            self.debug('title: %r', cp.title)
            defer.returnValue((cp, decoded))
        else:
            print 'ERROR:', result
            defer.returnValue(None)
