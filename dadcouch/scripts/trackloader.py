# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# loads track pickles into the db

import sys
import pickle
import optparse

from couchdb import client

from dad.common import log

from dadcouch.model import lookup, couch
from dadcouch.selecter import couch as couchs

def load(opts, path):
    server = client.Server('http://localhost:5984')
    # FIXME: put this in quotes and see a 500 that gets unhandled
    cdb = server[opts.database]

    print 'Loading pickle', path
    handle = open(path)
    d = pickle.load(handle)
    for path, l in d.items():
        # apparently we saved as str; decode to utf-8
        if type(path) is str:
            path = path.decode('utf-8')
        assert type(path) is unicode

        if not path:
            print 'ERROR: no path', path
            continue

        try:
            audiofile = lookup.getAudioFile(cdb, path)
        except KeyError, e:
            print 'WARNING: %s not in database' % path
            continue
        except Exception, e:
            print log.getExceptionMessage(e)
            raise
            
        #print audiofile, type(audiofile)
        if not audiofile:
            print audiofile, type(audiofile)
            print 'THOMAS: WARNING: %s not in database' % path
            continue

        for tm in l:
            # convert start and end to count in samples, based on 44100
            start = tm.start * 44100 / (10 ** 9)
            end = tm.end * 44100 / (10 ** 9)

            # only save if it doesn't yet exist
            log.debug('load', 'audiofile id %r, start %r, end %r' % (
                audiofile.id, start, end))
            result = couch.Slice.view(cdb, 'dad/slices-by-audiofile',
                key=[audiofile.id, start, end],
                include_docs=True)
            slices = list(result)

            if not slices:
                # save a slice with an empty track, to be filled in later
                slice = couch.Slice(audiofile_id=audiofile.id,
                start=start, end=end, peak=tm.peak,
                rms=tm.rms, rms_percentile=tm.rmsPercentile,
                rms_peak=tm.rmsPeak, rms_weighted=tm.rmsWeighted,
                attack=tm.attack, decay=tm.decay)
                assert type(tm.attack[0][1]) is long
                assert type(slice.attack[0][1]) is long
                if not opts.dryrun:
                    print 'INFO: saving slice %r for path %r' % (slice, path)
                    r = slice.store(cdb)
                    self.debug('store result: %r', r)
                else:
                    print 'INFO: dry run, not saving slice %r for path %r' % (
                        slice, path)
            else:
                slice = slices[0]
                print 'INFO: slice path %r, start %r, end %r, id %r exists' % (
                    path, start, end, slice.id)
                if not slice.attack or not slice.decay:
                    print 'INFO: but no attack/decay'
                    if not slice.attack:
                        slice.attack = tm.attack
                    if not slice.decay:
                        slice.decay = tm.decay
                    if not opts.dryrun:
                        print "INFO: Storing slice attack/decay"
                        slice.store(cdb)
                    else:
                        print "INFO: Dry run, not storing slice attack/decay"

            #return

class OptionParser(optparse.OptionParser):
    standard_option_list = couchs.couchdb_option_list + \
        [
            optparse.Option('-d', '--dry-run',
                action="store_true", dest="dryrun",
                help="Do not change database (defaults to %default)",
                default=False),
        ]
                
if __name__ == '__main__':
    log.init()

    parser = OptionParser()
    opts, args = parser.parse_args(sys.argv[1:])
    
    for path in args:
        load(opts, path)
