# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes.
"""

from dad.extern.log import log

# base class for model


class Model:
    pass


class View(log.Loggable):
    """
    I am a base class for views.
    """

    controller = None

    # FIXME: error ?

# FIXME: decide on snake case vs camelCase
class SelectorView(View):
    """
    I am a base class for selector widgets.
    """
    title = 'Selector, override me'

    def add_row(self, i, display, sort, tracks):
        """
        @param i:      an id
        @type i:       C{unicode}
        @type display: C{unicode}
        @type sort:    C{unicode}
        """
        raise NotImplementedError

    def throb(self, active=True):
        """
        Start or stop throbbing the selector to indicate activity.

        @param active: whether to throb
        """
        pass


class Controller(log.Loggable):
    """
    I am a base class for controllers.

    @type: subclass of L{Controller}
    """

    parent = None

    # FIXME: self._model is used in subclasses

    def __init__(self, model):
        """
        @type  model: L{Model}
        """
        self._model = model
        self._views = []
        self._controllers = []

    ### base class methods

    def addView(self, view):
        self._views.append(view)
        view.controller = self
        self.viewAdded(view)

    def doViews(self, method, *args, **kwargs):
        for view in self._views:
            m = getattr(view, method)
            m(*args, **kwargs)

    def add(self, controller):
        self._controllers.append(controller)
        controller.parent = self

    def getRoot(self):
        """
        Get the root controller forr this controller.

        @rtype: subclass of L{Controller}
        """
        parent = self.parent
        while parent.parent:
            parent = parent.parent

        return parent

    ### subclass methods

    def viewAdded(self, view):
        """
        This method is called after a view is added.
        It can be used to connect to signals on the view.
        """
        pass

