# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Twisted + Logger commands.
"""

from dad.common import logcommand
from dad.extern.command import tcommand


class TwistedCommand(tcommand.TwistedCommand, logcommand.LogCommand):
    pass

class LogReactorCommand(tcommand.ReactorCommand, logcommand.LogCommand):
    pass
