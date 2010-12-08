# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# migrate dad to the django-based one

import os
import sys
import MySQLdb


from couchdb import client

from dad.common import mapping
from dad.model import couch, lookup

db = MySQLdb.connect(user='root', db='dad')

server = client.Server('http://localhost:5984')
cdb = server['dad']

def _listsEqual(l1, l2):
    d1 = [a for a in l1 if a not in l2]
    d2 = [a for a in l2 if a not in l1]

    return not d1 and not d2

def categories(db):
    categoryids = {}

    # migrate categories
    db.query('SELECT * from category')
    r = db.use_result()

    view = couch.Category.view(cdb, 'dad/categories', include_docs=True)
    categories = dict([(c.name, c) for c in view])

    for i, name in r.fetch_row(maxrows=0):
        if name not in categories:
            print 'adding Category', name
            category = couch.Category(name=name)
            category.store(cdb)
        else:
            category = categories[name]

        print name, category.id

        categoryids[i] = category
    return categoryids

def users(db):
    userids = {}

    # migrate categories
    db.query('SELECT * from users')
    r = db.use_result()

    view = couch.User.view(cdb, 'dad/users', include_docs=True)
    users = dict([(u.name, u) for u in view])

    for row in r.fetch_row(maxrows=0, how=1):
        name = row['username'].decode('utf-8')
        i = row['user_id']

        if name not in users:
            print 'adding User', name
            user = couch.User(name=name)
            user.store(cdb)
        else:
            user = users[name]

        print name, user.id

        userids[i] = user
    return userids


def artists(db):
    print '+ artists'
# migrate artists
    artistids = {}
    db.query('SELECT artist_id, artistname from artist')
    r = db.use_result()
    for row in r.fetch_row(maxrows=0, how=1):
        name = row['artistname'].decode('utf-8')
        i = row['artist_id']

        view = couch.Artist.view(cdb, 'dad/artists', key=name,
            include_docs=True)
        artists = list(view)

        if not artists:
            print 'adding Artist', name
            artist = couch.Artist(name=name, sortname=name, displayname=name)
            artist.store(cdb)
        else:
            artist = artists[0]

        artistids[i] = artist

        print name, artist.id

    return artistids

def albums(db, artistids):
    print '+ albums'
    # migrate albums
    albumids = {}
    db.query('''
        SELECT * from album
    ''')
    r = db.use_result()
    for row in r.fetch_row(maxrows=0, how=1):
        name = row['title'].decode('utf-8')
        db.query('''
            SELECT * from albumxartist
            WHERE album_id=%s
        ''' % row['album_id'])
        r2 = db.use_result()
        artists = []
        for row2 in r2.fetch_row(maxrows=0, how=1):
            artists.append(artistids[row2['artist_id']])

        view = couch.Album.view(cdb, 'dad/albums', key=name,
            include_docs=True)
        albums = list(view)

        # filter this list based on the same set of artists we are looking for
        albums = qsFilterArtists(albums, artists)

        if len(list(albums)) > 1:
            raise AssertionError, "more than one combo: %r" % albums

        album = None

        if albums:
            album = albums[0]

        if not album:
            print 'adding Album', name.encode('utf-8')
            # uniqify artists by zipping a dict on name; apparently dad had multiple same albumxartist entries
            artists = dict([(a.name, a.id) for a in artists]).values()
            print 'THOMAS: zipped artists', artists

            album = couch.Album(name=name, artist_ids=artists)
            album.store(cdb)

        albumids[row['album_id']] = album
        print name, album.id

    return albumids


def audiofiles(db):
    print '+ audiofiles'
    # migrate audiofile
    audiofileids = {}
    db.query('''
        SELECT * from audiofile JOIN paths
        WHERE audiofile.path_id=paths.path_id
    ''')
    r = db.use_result()
    for row in r.fetch_row(maxrows=0, how=1):

        # construct path, which ought to be unique
        path = row['path'].decode('utf-8')
        if path.startswith('/'): path = path[1:] # bug in dad database
        dirpath = os.path.join(u'/opt/davedina/audio', path)
        filename = row['filename'].decode('utf-8')
        path = os.path.join(dirpath, filename)
        try:
            directory = lookup.findOrAddDirectory(cdb, dirpath)
        except Exception, e:
            print e
            print 'ERROR: could not find directory', dirpath
            continue
        if not directory:
            continue

        result = couch.AudioFile.view(cdb, 'dad/audiofile-lookup',
            key=[filename, directory.id],
            include_docs=True)
        audiofiles = list(result)

        if not audiofiles:
            print 'adding AudioFile', path.encode('utf-8')
            audiofile = lookup.findOrAddAudioFile(cdb, directory, filename)
        else:
            audiofile = audiofiles[0]

        audiofileids[row['audiofile_id']] = audiofile
    return audiofileids

def qsFilterArtists(result, artists):
    # type artists: list of couch.Artist

    # filter the given result set on items with exactly the same unordered
    # list of artist ids

    # returns a list of models that match

    ret = []

    # only keep albums where each of the given artists is an artist
    for artist in artists:
        result = [r for r in result if artist.id in r.artist_ids]

    # now make sure there are no more artists
    if result:
        for item in result:
            if _listsEqual(item.artist_ids, [a.id for a in artists]):
                ret.append(item)

    return ret

def audios(db, audiofileids, artistids, albumids):
    print '+ audios'
    # migrate audios
    audioids = {}
    db.query('''
        SELECT * from audio
    ''')
    r = db.use_result()
    for row in r.fetch_row(maxrows=0, how=1):
        name = row['title'].decode('utf-8')
        db.query('''
            SELECT * from audioxartist
            WHERE audio_id=%s
        ''' % row['audio_id'])
        r2 = db.use_result()
        artists = []
        for row2 in r2.fetch_row(maxrows=0, how=1):
            artists.append(artistids[row2['artist_id']])

        view = couch.Track.view(cdb, 'dad/tracks', key=name,
            include_docs=True)
        tracks = list(view)

        # filter this list based on the same set of artists we are looking for
        result = qsFilterArtists(tracks, artists)

        if len(result) > 1:
            raise AssertionError, "more than one combo", result

        track = None

        if result:
            track = result[0]

        if not track:
            print 'adding Track', name.encode('utf-8')
            # uniqify artists by zipping a dict on name; apparently dad had multiple same albumxartist entries
            artists = dict([(a.name, a.id) for a in artists]).values()
            print 'THOMAS: zipped artists', artists

            track = couch.Track(name=name, artist_ids=artists)
            track.store(cdb)


        # create the audiofile association
        afid = int(row['audiofile_id'])
        audiofile = audiofileids[afid]

        # FIXME: slices
        #for slice in models.Slice.objects.filter(audiofile=audiofile):
        result = couch.Slice.view(cdb, 'dad/slice-lookup',
            startkey=[audiofile.id, None, None],
            endkey=[audiofile.id + 'a', None, None],
            include_docs=True)
        slices = list(result)
        for slice in slices:
            print 'setting track %r on slice %r' % (track, slice)
            slice.track_id = track.id
            slice.store(cdb)

 
        # create the album association
        aid = row['album_id']
        if aid == 0L:
            if lookup.file_getPath(cdb, audiofile).find('/songs/') == -1:
                # For example, What Jail Is Like (live) from the bootlegs
                print 'WARNING: track %r does not have album info' % track
        else:  
            try:
                album_id = row['album_id']
                album = albumids[album_id]
            except KeyError:
                print 'ERROR: could not look up album_id %d for track %r' % (
                    album_id, track)
                return

            number = row['track']


            view = couch.Track.view(cdb, 'dad/trackalbum-lookup',
                key=[track.id, album.id, number],
                include_docs=True)
            trackalbums = list(view)

            if not trackalbums:
                ta = couch.TrackAlbum(
                    track_id=track.id, album_id=album.id, number=number)
                ta.store(cdb)
                print 'looked up album %r for track %r' % (album, track)

        audioids[row['audio_id']] = track
    return audioids

def scores(db, categoryids, userids, audioids):
    print '+ scores'
    db.query('''
        SELECT * from score
    ''')
    r = db.use_result()
    scores = {} # dict of user_id, track_id -> dict of category_id -> score

    for row in r.fetch_row(maxrows=0, how=1):
        try:
            track_id = audioids[row['audio_id']].id
            user_id = userids[row['user_id']].id
            category_id = categoryids[row['cat_id']].id
            rate = int(row['rate'] * 1000.0) / 1000.0
        except KeyError:
            print 'ERROR: could not lookup something in row', row
            continue

        if (user_id, track_id) not in scores.keys():
            scores[(user_id, track_id)] = {}
        scores[(user_id, track_id)][category_id] = rate

    for (user_id, track_id) in scores.keys():
        score = couch.Score(user_id=user_id,
            subject_type='track', subject_id=track_id)
        for category_id, rate in scores[user_id, track_id].items():
            score.scores.append(category_id=category_id, score=rate)

        # FIXME: no sqlite, so don't use IntegrityError, but lookup first
        try:
            score.store(cdb)
            print 'rated user_id %r, track_id %r: %r' % (
                user_id, track_id, score.scores)
            print 'score', score.id

        except db.IntegrityError:
            # already in
            print 'WARNING: track %r already rated, score %r' % (track_id, score)
            pass
 
categoryids = categories(db)
userids = users(db)
artistids = artists(db)
albumids = albums(db, artistids)
audiofileids = audiofiles(db)

audioids = audios(db, audiofileids, artistids, albumids)

scores(db, categoryids, userids, audioids)
sys.exit(0)
