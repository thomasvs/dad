# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# loads track pickles into the db

import sys
import pickle

from couchdb import client

from dad.model import lookup, couch

server = client.Server('http://localhost:5984')
cdb = server['dad']

def load(path):
    handle = open(path)
    d = pickle.load(handle)
    for path, l in d.items():
        # apparently we saved as str; decode to utf-8
        if type(path) is str:
            path = path.decode('utf-8')
        assert type(path) is unicode

        if not path:
            print 'THOMAS: ERROR: no path', path
            continue

        try:
            audiofile = lookup.getAudioFile(cdb, path)
        except Exception, e:
            print e
            print path, type(path)
            print 'THOMAS: WARNING: %s not in database' % path
            continue
            
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
            print 'THOMAS: key', audiofile.id, start, end
            result = couch.Slice.view(cdb, 'dad/slice-lookup',
                key=[audiofile.id, start, end],
                include_docs=True)
            slices = list(result)

            if not slices:
                slice = couch.Slice(audiofile_id=audiofile.id,
                start=start, end=end, peak=tm.peak,
                rms=tm.rms, rms_percentile=tm.rmsPercentile,
                rms_peak=tm.rmsPeak, rms_weighted=tm.rmsWeighted,
                attack=tm.attack, decay=tm.decay)
                print 'THOMAS: saving slice', slice
                assert type(tm.attack[0][1]) is long
                assert type(slice.attack[0][1]) is long
                print slice.store(cdb)
            else:
                print 'THOMAS: slice already there', slice

            return

                
for path in sys.argv[1:]:
    load(path)
