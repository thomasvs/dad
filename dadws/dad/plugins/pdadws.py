# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding WebSocket-based functionality to dad command

from zope import interface
from twisted import plugin

from dad import idad

class WSPlayerProvider(object):
    interface.implements(plugin.IPlugin, idad.IPlayerProvider)

    name = 'ws'

    def getOptions(self):
        from dadws import player
        return player.ws_player_option_list

    def getPlayer(self, scheduler, options):
        from dadws import player
        return player.WebSocketPlayer(scheduler)


# instantiate twisted plugins
_wspp = WSPlayerProvider()
