# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes.
"""

from dad.extern.log import log

# base class for model


class Model(log.Loggable):

    logCategory = 'model'

    pass


class View(log.Loggable):
    """
    I am a base class for views.
    """


class SelectorView(View):
    """
    I am a base class for selector widgets.
    """
    title = 'Selector, override me'

    def add_row(self, i, display, sort, tracks):
        raise NotImplementedError

    def throb(self, active=True):
        """
        Start or stop throbbing the selector to indicate activity.

        @param active: whether to throb
        """
        pass


class Controller(log.Loggable):

    def __init__(self, model):
        self._model = model
        self._views = []

    ### base class methods

    def addView(self, view):
        self._views.append(view)
        self.viewAdded(view)

    def doViews(self, method, *args, **kwargs):
        for view in self._views:
            m = getattr(view, method)
            m(*args, **kwargs)

    ### subclass methods

    def viewAdded(self, view):
        """
        This method is called after a view is added.
        It can be used to connect to signals on the view.
        """
        pass

