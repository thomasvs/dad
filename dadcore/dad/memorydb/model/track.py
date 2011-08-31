# -*- Mode: Python; test_case_name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.model import track
from dad.memorydb.model import base

# FIXME: should subclass from base; __init__ needs fixing
class MemoryTrackModel(track.TrackModel):
    """
    @ivar id:     id of the track
    @ivar scores: list of L{data.Score}
    """

    def __init__(self, id):
        self.id = id
        self.scores = []
        self.fragments = []
        self.name = None

    # base class implementations

    def addFragment(self, info, metadata=None, mix=None, number=None):
        fragment = track.FragmentModel()
        file = track.FileModel()
        file.info = info
        file.metadata = metadata

        fragment.files.append(file)
        self.fragments.append(fragment)
    
    def getName(self):
        if self.name:
            return self.name

        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata:
                    return file.metadata.title

    def getArtists(self):
        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata and file.metadata.artist:
                    return [file.metadata.artist, ]

        return []

    def getArtistIds(self):
        return self.getArtists()


    def getFragments(self):
        return self.fragments
        
    # FIXME: need more ?
    def get(self, subjectId):
        return defer.succeed(self)

    # specific methods
    # FIXME: handle this better in both models
    def filesAppend(self, files, info, metadata=None, number=None):
        file = track.FileModel()
        file.info = info
        file.metadata = metadata
        file.number = number

        files.append(file)

class MemoryTrackSelectorModel(track.TrackSelectorModel, base.MemoryModel):
    def get(self):
        return defer.succeed(self._db._tracks.values())