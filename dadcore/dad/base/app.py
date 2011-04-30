# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes.
"""

from twisted.python import reflect

from dad.extern.log import log

from dad.base import base

# base class for model


class AppModel(base.Model):

    logCategory = 'appmodel'

    pass


class AppView(base.View):
    """
    I am a base class for an application view.
    """

    # FIXME: error ?

class AppController(base.Controller):

    def getTriad(self, what):
        # ex. model: dadcouch.model.daddb.TrackModel
        #            dad.controller.trackTrackController
        #            dadgtk.views.track.TrackView
        model = self._model.getModel(what)
        cklazz = 'dad.controller.%s.%sController' % (what.lower(), what)
        controller = reflect.namedAny(cklazz)(model)
        views = []
        for v in self._views:
            view = v.getView(what)
            controller.addView(view)
            views.append(view)

        return (controller, model, views)
