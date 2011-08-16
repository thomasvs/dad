# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding GStreamer-based functionality to dad command

import os

from zope import interface
from twisted import plugin

from dadgst.task import level
from dad import idad

from dadgst.command import analyze

# twisted.plugin interface
class CommandAppender(object):
    interface.implements(plugin.IPlugin, idad.ICommand)

    def addCommands(self, commandClass):
        commandClass.subCommandClasses.append(analyze.Analyze)


class GstMetadataGetter(object):
    interface.implements(plugin.IPlugin, idad.IMetadataGetter)

    def getMetadata(self, path, runner=None):
        if not runner:
            runner = task.SyncRunner()

        import gobject
        gobject.threads_init()

        t = level.TagReadTask(path)
        runner.run(t)

        from dad.logic import database
        metadata = database.TrackMetadata()

        import gst
        mapping = {
            gst.TAG_ARTIST:              'artist',
            gst.TAG_TITLE:               'title',
            gst.TAG_ALBUM:               'album',
            gst.TAG_TRACK_NUMBER:        'trackNumber',
            gst.TAG_AUDIO_CODEC:         'audioCodec',
            'musicbrainz-trackid':       'mbTrackId',
            'musicbrainz-artistid':      'mbArtistId',
            'musicbrainz-albumid':       'mbAlbumId',
            'musicbrainz-albumartistid': 'mbAlbumArtistId',
        }

        for key, value in mapping.items():
            if key in t.taglist:
                setattr(metadata, value, t.taglist[key])

        # date handling: we have GstDate with .date, .month, .year 
        if gst.TAG_DATE in t.taglist:
            for key in ['year', 'month', 'day']:
                setattr(metadata, key, getattr(t.taglist[gst.TAG_DATE], key))

        metadata.channels = t.channels
        metadata.rate = t.rate
        metadata.length = t.length

        return metadata
    

class GstLeveller(object):
    interface.implements(plugin.IPlugin, idad.ILeveller)

    def getTrackMixes(self, path, runner=None):
        if not runner:
            runner = task.SyncRunner()

        import gobject
        gobject.threads_init()

        t = level.LevellerTask(path)
        runner.run(t)

        return t.get_track_mixes()
    

# instantiate twisted plugins
_ca = CommandAppender()
_gmg = GstMetadataGetter()
_gl = GstLeveller()
