# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

from dad.common import log
from dad.base import base

class SelectorModel(base.Model, log.Loggable):
    """
    I am a model to select items from a list.
    """

    logCategory = 'selectormodel'

    def get(self):
        """
        @returns: a deferred firing a list of L{base.Model}
        """
        raise NotImplementedError
