# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

if __name__ == '__main__':
    # twisted.web.http imports reactor
    # FIXME: fix that so we can move this install to main
    from twisted.internet import gtk2reactor
    gtk2reactor.install()

import os
import sys
import optparse

import gtk

from twisted.internet import defer
from twisted.python import failure, reflect

from dad.base import base, app
from dad.extern.log import log

from dadcouch.model import daddb
from dadcouch.model import couch
from dadcouch.selecter import couch as scouch

from dadcouch.extern.paisley import client

from dadgtk.views import track as trackv, app as appv
from dad.controller import track as trackc

def main():

    from twisted.internet import reactor


    from twisted.internet import defer
    defer.Deferred.debug = 1

    log.init('DAD_DEBUG')
    log.logTwisted()
    log.debug('main', 'start')

    parser = optparse.OptionParser()
    parser.add_options(scouch.couchdb_option_list)
    parser.add_options(scouch.user_option_list)
    options, args = parser.parse_args()

    try:
        title = args[0]
    except:
        title = 'Love'

    # FIXME: allow customizing model and/or view(s)
    modelType = 'Couch'
    viewTypes = ['GTK', ]

    server = client.CouchDB(host=options.host, port=options.port)
    dbName = options.database
    db = daddb.DADDB(server, dbName)

    modelModule = 'dad%s.models.app.%sAppModel' % (modelType.lower(), modelType)
    amodel = reflect.namedAny(modelModule)(db)

    acontroller = app.AppController(amodel)

    for viewType in viewTypes:
        viewModule = 'dad%s.views.app.%sAppView' % (viewType.lower(), viewType)
        aview = reflect.namedAny(viewModule)()
        acontroller.addView(aview)

    # FIXME: gtk-specific
    aview.widget.connect('destroy', lambda _: reactor.stop())

    controller, model, views = acontroller.getTriad('Track')

    view = trackv.TrackView()
    view = views[0]

    aview.add(view)

    # start loading artists and albums

    d = defer.Deferred()

    # get the first track matching the arg for title
    
    # FIXME: add an exception for a missing view
    d.addCallback(lambda _:
        db.viewDocs('tracks', couch.Track, include_docs=True,
            startkey=title, endkey=title + 'Z'))
    def eb(failure):
        log.warningFailure(failure)
        print 'track.py: FAILURE: ', failure
        reactor.stop()
    d.addCallback(lambda g: list(g)[0].id)
    d.addCallback(lambda t: controller.populate(t, userName=options.user))
    d.addErrback(eb)


    d.callback(None)

    reactor.run()

if __name__ == '__main__':
    main()
