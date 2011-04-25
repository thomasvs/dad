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

from dad.base import base
from dad.extern.log import log

from dadcouch.model import daddb
from dadcouch.model import couch
from dadcouch.selecter import couch as scouch

from dadcouch.extern.paisley import client

from dadgtk.views import track


# move to base class
class TrackController(base.Controller):

    _track = None

    # FIXME: push to base class
    def __init__(self, model):
        base.Controller.__init__(self, model)

    def viewAdded(self, view):
        view.connect('scored', self._scored)

    
    def _scored(self, view, category, score):
        print 'THOMAS: scored', category, score
        # FIXME: user ?
        # FIXME: make interface for this model
        self._model.score(self._track, 'thomas', category, score)

    def populate(self, trackId, userName=None):
        assert type(trackId) is unicode
        self.debug('populate(): trackId %r', trackId)
        # self.doViews('throb', True)

        # populate with the Track
        d = self._model.get(trackId)

        def cb(t):
            self._track = t
            self.debug('populating')
            self.doViews('set_artist', " & ".join(
                [a.name for a in t.artists]))
            self.doViews('set_title', t.name)
            self.debug('populated')
        d.addCallback(cb)

        def eb(failure):
            self.warningFailure(failure)
            self.doViews('error', "failed to populate",
                "%r: %r" % (failure, failure.value.args))
        d.addErrback(eb)

        d.addCallback(lambda _: self._model.getScores(userName=userName))
        def getScoresCb(scores):
            # scores: list of couch.Score with resolutions
            for s in scores:
                for score in s.scores:
                    # FIXME: user
                    self.doViews('set_score', score['category']['name'],
                        score['score'])


        d.addCallback(getScoresCb)
        return d

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

    server = client.CouchDB(host=options.host, port=options.port)
    dbName = options.database
    db = daddb.DADDB(server, dbName)

    window = gtk.Window()
    window.connect('destroy', lambda _: reactor.stop())

    view = track.TrackView()

    window.add(view.widget)


    model = daddb.TrackModel(db)
    controller = TrackController(model)
    controller.addView(view)


    window.set_default_size(640, 480)

    window.show_all()

    # start loading artists and albums

    d = defer.Deferred()

    # get the first track matching the arg for title
    
    # FIXME: add an exception for a missing view
    d.addCallback(lambda _:
        db.viewDocs('tracks', couch.Track, include_docs=True,
            startkey=title, endkey=title + 'Z'))
    def eb(failure):
        print 'FAILURE: ', failure
        reactor.stop()
    d.addCallback(lambda g: list(g)[0].id)
    d.addCallback(lambda t: controller.populate(t, userName=options.user))
    d.addErrback(eb)


    d.callback(None)

    reactor.run()

if __name__ == '__main__':
    main()
