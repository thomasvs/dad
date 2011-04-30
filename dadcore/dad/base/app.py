# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes.
"""

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
    pass

