# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

from twisted.internet import defer

from dad.model import track
from dad.memorydb.model import base

class MemoryTrackModel(track.TrackModel, base.MemoryModel):
    """
    @ivar scores: list of L{data.Score}
    """

    def __init__(self, memorydb, id=None):
        base.MemoryModel.__init__(self, memorydb)

        self.id = id

        self.scores = []
        self.fragments = []
        self.name = None

    # base class implementations

    def new(self, db, name, sort=None, mbid=None, id=None):
        if not sort:
            sort = name

        model = MemoryTrackModel(db, id)
        model.name = name
        model.sortName = sort
        model.mbid = mbid
        return model
    new = classmethod(new)

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

    def setName(self, name):
        self.name = name

    # FIXME: should this be in the iface ?
    def getId(self):
        return self.id

    def getArtistNames(self):
        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata and file.metadata.artist:
                    return [file.metadata.artist, ]

        return []

    @defer.inlineCallbacks
    def getArtists(self):
        models = []

        for fragment in self.fragments:
            for file in fragment.files:
                if not file.metadata:
                    continue

                # metadata only lists one artist
                am = yield self._db.newArtist(
                    name=file.metadata.artist,
                    mbid=file.metadata.mbArtistId)
                models.append(am)

        defer.returnValue((m for m in models))

    def getArtistNames(self):
        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata and file.metadata.artist:
                    return [file.metadata.artist, ]

        return []


    def getArtistIds(self):
        return self.getArtistNames()

    def getArtistMids(self):
        for fragment in self.fragments:
            for file in fragment.files:
                if file.metadata and file.metadata.mbArtistId:
                    return ['artist:mbid:' + file.metadata.mbArtistId, ]
                if file.metadata and file.metadata.artist:
                    return ['artist:name:' + file.metadata.artist, ]


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
