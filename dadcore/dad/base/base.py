# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes.
"""

from dad.extern.log import log

# base class for model


class Model:
    """
    I am a base class for models.
    I hold data coming from a database that can be presented in a view
    through the controller.
    """

    pass


class View(log.Loggable):
    """
    I am a base class for views.

    @ivar controller: L{Controller}
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
        @param i:       an id
        @param i:       a unique id for the row that allows the model to look up
                        the original object.
        @type  i:       C{unicode}
        @param display: the display name of the item
        @type  display: C{unicode}
        @type  sort:    C{unicode}
        @param tracks:  the number of tracks 
        @type  tracks:  int
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
    I interact with one model and one or more views.

    @type parent: L{Controller}
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
        """
        @type  view: L{View}
        """
        self._views.append(view)
        view.controller = self
        self.viewAdded(view)

    def doViews(self, method, *args, **kwargs):
        """
        Call the given method on all my views, with the given args and kwargs.
        """
        for view in self._views:
            m = getattr(view, method)
            m(*args, **kwargs)

    def add(self, controller):
        """
        Add a child controller to me.
        Takes parentship over the controller.

        @type controller: subclass of L{Controller}
        """
        self._controllers.append(controller)
        controller.parent = self

    def getRoot(self):
        """
        Get the root controller for this controller.

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

        @type  view: L{View}
        """
        pass
