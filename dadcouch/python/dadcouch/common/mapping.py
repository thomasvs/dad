# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# FIXME: this should really go away
try:
    from dadcouch.extern.paisley.mapping import *
except ImportError, e:
    print 'OHOH', e
    from couchdb.schema import *
