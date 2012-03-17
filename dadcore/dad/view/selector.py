# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.base import base

# FIXME: decide on snake case vs camelCase
class SelectorView(base.View):
    """
    I am a base class for selector widgets.
    """
    title = 'Selector, override me'

    def add_row(self, item, display, sort, tracks):
        """
        @param item:    an item that can serve as a model for an individual
                        item view
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
