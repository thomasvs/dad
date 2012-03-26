# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes.
"""

from twisted.python import reflect

from dad.base import base

# base class for model


class AppModel(base.Model):

    logCategory = 'appmodel'

    def __init__(self, database):
        self.database = database

    def getModel(self, what):
        """
        Get a model from the application for the given item.

        @type  what: str
        @param what: one of Track, Artist, Album
        """
        raise NotImplementedError


class AppView(base.View):
    """
    I am a base class for an application view.
    """

    # FIXME: error ?

    def getView(self, what):
        """
        Get a view from the application for the given item.

        @type  what: str
        @param what: one of Track, Artist, Album
        """
        raise NotImplementedError


class AppController(base.Controller):

    def getTriad(self, what, model=None):
        # ex. model: dadcouch.model.daddb.TrackModel
        #            dad.controller.trackTrackController
        #            dadgtk.views.track.TrackView
        if not model:
            model = self._model.getModel(what)

        whats = {
            'ArtistSelector': 'selector.ArtistSelectorController',
            'AlbumSelector': 'selector.AlbumSelectorController',
            'TrackSelector': 'selector.TrackSelectorController',
        }
        cklazz = 'dad.controller.%s.%sController' % (what.lower(), what)
        if what in whats:
            cklazz = 'dad.controller.%s' % whats[what]

        try:
            controller = reflect.namedAny(cklazz)(model)
        except AttributeError:
            raise AttributeError("Could not reflect %r" % cklazz)

        # FIXME: should we set ourselves as the parent or not if not set ?
        controller.parent = self

        views = []
        for v in self._views:
            view = v.getView(what)
            controller.addView(view)
            views.append(view)

        return (controller, model, views)
