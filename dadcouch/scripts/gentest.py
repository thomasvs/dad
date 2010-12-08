# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# make a smaller test copy of the database that is consistent by only
# getting a few artists


import os
import sys

from twisted.internet import defer

from dad.extern.paisley import couchdb, views, mapping

from dad.model import couch, lookup, daddb
from dad.common import log

def ref(refs, cache, klazz, attribute):
    # create backreference from objects pointed to by the attribute
    # for example:
    # Album, artists
    # will create a dict of artist id -> album ids

    # (klazz, attribute) -> dict of referenced id -> referring id
    refs[(klazz, attribute)] = {}
    d = refs[(klazz, attribute)]

    isList = False
    attr = getattr(klazz, attribute)
    if isinstance(attr, mapping.ListField):
        isList = True

    for item in cache[klazz].values():
        values = getattr(item, attribute)
        if not isList:
            values = [getattr(item, attribute), ]

        for v in values:
            if v not in d.keys():
                d[v] = []
            d[v].append(item.id)

def cacheLoad(cache, dadDB, klazz, view):
    log.debug('cacheLoad', 'Loading klazz %r using view %r', klazz, view)
    cache[klazz] = {}

    d = dadDB.viewDocs(view, klazz, include_docs=True)
    def cb(result):
        for item in result:
            cache[klazz][item.id] = item
    d.addCallback(cb)
    return d


def slice(dadDB, count=1):
    # slice out 10 artist docs and related ones

    # loads each 'table' into a dict of id -> object
    cache = {} # class -> all docs of that class
    dump = {}
    refs = {} # class, attribute -> dict of attribute id -> object id

    d = defer.Deferred()

    for klazz, view in [
        (couch.Artist, 'artists'),
        (couch.Album, 'albums'),
        (couch.TrackAlbum, 'trackalbum-lookup'),
        (couch.Track, 'tracks'),
        (couch.Slice, 'slice-lookup'),
        #(couch.File, 'files'),
        (couch.AudioFile, 'audiofile-lookup'),
        (couch.Volume, 'volumes'),
        (couch.Directory, 'directory-lookup'),
        (couch.Category, 'categories'),
        (couch.User, 'users'),
        (couch.Score, 'track-score'),
    ]:
        dump[klazz] = {} # object => True

        d.addCallback(lambda _, k, v: cacheLoad(cache, dadDB, k, v),
            klazz, view)

    for klazz, attribute in [
        (couch.Track, 'artist_ids'),
        (couch.Album, 'artist_ids'),
        (couch.TrackAlbum, 'album_id'),
        (couch.TrackAlbum, 'track_id'),
        (couch.Slice, 'track_id'),
        (couch.Slice, 'audiofile_id'),
        (couch.AudioFile, 'directory_id'),
        (couch.Directory, 'parent_id'),
        (couch.Directory, 'volume_id'),
        (couch.Score, 'subject_id'),
    ]:
        d.addCallback(lambda _, k, a: ref(refs, cache, k, a),
            klazz, attribute)

    def addArtist(dump, artistId, back=False):
        if artistId in dump[couch.Artist].values():
            return

        log.debug('gentest', 'adding artist %s', artistId)
        artist = cache[couch.Artist][artistId]
        dump[couch.Artist][artist] = artist.id

        if not back:
            return

        # albums point to artists
        d = refs[(couch.Album, 'artist_ids')]
        if artistId in d:
            for albumId in d[artistId]:
                addAlbum(dump, albumId)

        d = refs[(couch.Track, 'artist_ids')]
        if artistId in d:
            for trackId in d[artistId]:
                addTrack(dump, trackId)

    def addAlbum(dump, albumId):
        if albumId in dump[couch.Album].values():
            return

        album = cache[couch.Album][albumId]
        log.debug('gentest', 'adding album %r' % album)
        dump[couch.Album][album] = album.id

        # trackalbums point to albums
        d = refs[(couch.TrackAlbum, 'album_id')]
        if albumId in d:
            for trackalbumId in d[albumId]:
                addTrackAlbum(dump, trackalbumId)

        # albums have artists
        for artist in album.artist_ids:
            addArtist(dump, artist, back=False)

    def addTrack(dump, trackId):
        if trackId in dump[couch.Track].values():
            return

        track = cache[couch.Track][trackId]
        log.debug('gentest', 'adding track %r' % track)
        dump[couch.Track][track] = track.id

        # trackalbums point to tracks
        d = refs[(couch.TrackAlbum, 'track_id')]
        if trackId in d:
            for trackalbumId in d[trackId]:
                addTrackAlbum(dump, trackalbumId)

        # slices point to tracks
        d = refs[(couch.Slice, 'track_id')]
        if trackId in d:
            for sliceId in d[trackId]:
                addSlice(dump, sliceId)

        # tracks have artists
        for artist in track.artist_ids:
            addArtist(dump, artist, back=False)

        # scores point to tracks
        d = refs[(couch.Score, 'subject_id')]
        if trackId in d:
            for scoreId in d[trackId]:
                addScore(dump, scoreId)

    def addTrackAlbum(dump, trackalbumId):
        if trackalbumId in dump[couch.TrackAlbum].values():
            return

        trackalbum = cache[couch.TrackAlbum][trackalbumId]
        log.debug('gentest', 'adding trackalbum %r' % trackalbum)
        dump[couch.TrackAlbum][trackalbum] = trackalbum.id

        addAlbum(dump, trackalbum.album_id)
        addTrack(dump, trackalbum.track_id)

    def addSlice(dump, sliceId):
        if sliceId in dump[couch.Slice].values():
            return

        slice = cache[couch.Slice][sliceId]
        log.debug('gentest', 'adding slice %r' % slice)
        dump[couch.Slice][slice] = slice.id

        # slices point to tracks
        addTrack(dump, slice.track_id)

        # slices point to audiofiles
        addAudioFile(dump, slice.audiofile_id)

    def addScore(dump, scoreId):
        if scoreId in dump[couch.Score].values():
            return

        score = cache[couch.Score][scoreId]
        log.debug('gentest', 'adding score %r' % score)
        dump[couch.Score][score] = score.id

        # category and user are all dumped, so all in

    def addAudioFile(dump, audiofileId):
        if audiofileId in dump[couch.AudioFile].values():
            return

        audiofile = cache[couch.AudioFile][audiofileId]
        log.debug('gentest', 'adding audiofile %r' % audiofile)
        dump[couch.AudioFile][audiofile] = audiofile.id

        # audiofiles point to directories
        addDirectory(dump, audiofile.directory_id)

    def addDirectory(dump, directoryId):
        if directoryId in dump[couch.Directory].values():
            return

        directory = cache[couch.Directory][directoryId]
        log.debug('gentest', 'adding directory %r' % directory)
        dump[couch.Directory][directory] = directory.id

        # directories point to directories
        if directory.parent_id:
            addDirectory(dump, directory.parent_id)

        # directories point to volumes
        if directory.volume_id:
            addVolume(dump, directory.volume_id)

    def addVolume(dump, volumeId):
        if volumeId in dump[couch.Volume].values():
            return

        volume = cache[couch.Volume][volumeId]
        log.debug('gentest', 'adding volume %r' % volume)
        dump[couch.Volume][volume] = volume.id

    def cb(_):

        # here is where we output all id's
        artists = cache[couch.Artist].values()[:count]
        for artist in artists:
            log.debug('gentest', 'adding root artist %r', artist)
            addArtist(dump, artist.id, back=True)

        # now print all ids

        for klazz, d in dump.items():
            for i in d.values():
                print i

        # these are dumped integrally
        categories = cache[couch.Category].values()
        for category in categories:
            print category.id

        users = cache[couch.User].values()
        for user in users:
            print user.id

        return

    d.addCallback(cb)

    d.callback(None)

    return d

def main():
    log.init()

    # this rebinds and makes it break in views
    # db = couchdb.CouchDB('localhost', dbName='dad')
    db = couchdb.CouchDB('localhost')
    dadDB = daddb.DADDB(db, 'dad')
    d = slice(dadDB)
    d.addCallback(lambda _: reactor.stop())
    return d

from twisted.internet import reactor

reactor.callLater(0, main)
reactor.run()

