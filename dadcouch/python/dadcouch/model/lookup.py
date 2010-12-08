# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import os
import time
import stat
import md5

from twisted.internet import defer

from dadcouch.extern.paisley import views

from dad.common import log
from dadcouch.model import couch

def getAudioFile(db, path):
    """
    Get the AudioFile model object for the given path, or None.
    """
    directory, name = os.path.split(path)
    directory = findOrAddDirectory(db, directory, add=False)
    audiofile = findOrAddAudioFile(db, directory, name, add=False)
    return audiofile

def getVolumes(db):
    res = {}

    result = couch.Volume.view(db, 'dad/volumes', include_docs=True)
    for v in result:
        res[v.path] = v

    return res


def md5file(filename):
    """Return the hex digest of a file without loading it all into memory"""
    fh = open(filename)
    digest = md5.new()
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        digest.update(buf)
    fh.close()
    return digest.hexdigest()

def findVolume(db, path, volumes=None):
    """
    Given the path, find the Volume for that path.

    @returns: tuple of volume and rest of path
    @rtype:   tuple of (L{models.Volume}, str), or (None, None)
    """
    if not volumes:
        volumes = getVolumes(db)

    for vp in volumes.keys():
        if path.startswith(vp):
            volume = volumes[vp]

            # split the path and see if we can find it in the db
            rest = path[len(vp) + 1:]
            log.log('lookup', 'findVolume: returning %r', (volume, rest))
            return (volume, rest)

    print "Did not find volume for %s" % path
    raise KeyError, "Did not find volume for %s" % path
 
def findOrAddDirectory(db, path, volumes=None, add=True):
    if not volumes:
        volumes = getVolumes(db)
    volume, rest = findVolume(db, path, volumes)
    log.log('lookup', 'findOrAddDirectory: volume %r rest %r', volume, rest)

    # split the path and see if we can find it in the db
    parts = rest.split(os.path.sep)
    # FIXME: apparently os.path.split on a non-slashed dir still
    # returns a tuple with an empty string as first member
    if parts[0] is '':
        parts = parts[1:]

    # now find or add each part in turn in the db
    directory_id = None
    path = volume.path
    for part in parts:
        volume_id = volume and volume.id or None
        if os.path.sep in part:
            raise AssertionError, \
                "parts should not contain a part with /: %r" % (parts, )
        path = os.path.join(path, part)

        log.log('lookup', 'looking up directory on '
            'volume %r for path %s and part %s', volume, path, part)

        result = couch.Directory.view(db, 'dad/directory-lookup',
            key=[volume_id, directory_id, part],
            include_docs=True)
        result = list(result)

        if not result:
            if not add:
                return None

            res = os.stat(path)

            mtime = time.gmtime(res[stat.ST_MTIME])
            log.log('lookup', 'about to add Directory %r %r %r',
                part, volume, directory_id)
            directory = couch.Directory(name=part, volume_id=volume_id,
                parent_id=directory_id,
                mtime=mtime, inode=res[stat.ST_INO])
            directory.store(db)
        else:
            log.log('lookup', 'result %r %d', result, len(result))
            assert len(result) == 1
            directory = result[0]
        directory_id = directory.id

        volume = None # changes the first time through
        volume_id = None

    return directory

def file_getPath(db, file):
    # return the full path to the file using multiple db queries
    log.log('lookup', 'looking up path for file %r %r', file, file.id)
    directory = couch.Directory.load(db, file.directory_id)

    path = directory_getPath(db, directory)

    return os.path.join(path, file.name)


def directory_getPath(db, directory):
    # return the full path to the directory using multiple db queries
    parts = []

    log.log('lookup', 'looking up path for directory %r %r',
        directory, directory.id)
    while True:
        parts.append(directory.name)

        if directory.volume_id is not None:
            # gotten to the root, get volume path and stop
            volume = couch.Volume.load(db, directory.volume_id)
            parts.append(volume.path)
            break
        else:
            directory = couch.Directory.load(db, directory.parent_id)

    print parts
    parts.reverse()
    return "/".join(parts)


# if adding File works, and adding AudioFile fails (for example due to
# a constraint), we have a half-commited object.  Adding the decorator
# makes sure we have all or nothing.
def findOrAddAudioFile(db, directory, name, add=True, duration=0):
    # directory: Directory object
    result = couch.AudioFile.view(db, 'dad/audiofile-lookup',
            key=[name, directory.id],
            include_docs=True)
    result = list(result)

    if not result:
        if not add:
            return

        directoryPath = directory_getPath(db, directory)
        path = os.path.join(directoryPath, name)
        res = os.stat(os.path.join(directoryPath, name))

        mtime = time.gmtime(res[stat.ST_MTIME])
        sum = md5file(path)

        # FIXME: duration in DAD was not accurate, only hundreds of precision
        # so recalculate
        # We set it to 0 because we declared it non-NULL, which is a mistake
        audiofile = couch.AudioFile(name=name, directory_id=directory.id,
            mtime=mtime, inode=res[stat.ST_INO],
            size=res[stat.ST_SIZE], samplerate=44100,
            md5sum=sum)
        try:
            audiofile.store(db)
        except Exception, e:
            import code; code.interact(local=locals())
        return audiofile
    else:
        return result[0]

def load(db, dbName, klazz, viewName):
    """
    @type  db:       L{couchdb.CouchDB}
    @type  dbName:   str
    @param klazz:    the class to instantiate objects from
    @param viewName: name of the view to load objects from
    """
    log.debug('load', 'loading %s->%r using view %r',
        dbName, klazz, viewName)

    v = views.View(db, dbName, 'dad', viewName,
            klazz, include_docs=True)
    d = v.queryView()

    def eb(failure):
        log.warning('load', 'Failed to query view: %r',
            log.getFailureMessage(failure))
        return failure
    d.addErrback(eb)

    def cb(result):
        log.debug('load', 'loaded %s->%r using view %r',
            dbName, klazz, viewName)
        return result
    d.addCallback(cb)

    return d


def cacheLoad(cache, db, dbName, klazz, viewName):
    """
    @type  cache:    dict of class -> dict of id -> object
    @type  db:       L{couchdb.CouchDB}
    @type  dbName:   str
    @param klazz:    the class to instantiate objects from
    @param viewName: name of the view to load objects from
    """
    if klazz in cache.keys():
        return

    cache[klazz] = {}

    d = defer.Deferred()

    def eb(failure):
        log.warning('load', 'Failed to query view: %r',
            log.getFailureMessage(failure))
        return failure

    v = views.View(db, dbName, 'dad', viewName,
            klazz, include_docs=True)
    d = v.queryView()
    def cb(result):
        for item in result:
            cache[klazz][item.id] = item
    d.addCallback(cb)
    d.addErrback(eb)

    return d
