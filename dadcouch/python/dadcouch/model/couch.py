# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import datetime
import math

from dadcouch.extern.paisley import mapping

"""
Document mappings from CouchDB to python.
"""


# new documents
class Track(mapping.Document):
    type = mapping.TextField(default="track")

    name = mapping.TextField()

    artist_ids = mapping.ListField(mapping.TextField())
    artists = mapping.ListField(mapping.TextField())

    added = mapping.DateTimeField(default=datetime.datetime.now)
    
    # a track is represented by one or more fragments of files
    fragments = mapping.ListField(
        mapping.DictField(mapping.Mapping.build(
            # multiple files can share fragment info; for example
            # the same file on different computers, or the same encoding
            # with similar audio properties
            files = mapping.ListField(
                mapping.DictField(mapping.Mapping.build(
                    # each file is on a host
                    host = mapping.TextField(),
                    # and on a volume and path on that host
                    volume = mapping.TextField(),
                    volume_path = mapping.TextField(),
                    path = mapping.TextField(),
                    mtime = mapping.DateTimeField(),
                    size = mapping.IntegerField(),
                    md5sum = mapping.TextField(),

                    # and has metadata
                    metadata = mapping.DictField(mapping.Mapping.build(
                        artist = mapping.TextField(),
                        title = mapping.TextField(),
                        album = mapping.TextField(),
                        track_number = mapping.IntegerField(),
                        audio_codec = mapping.TextField(),
                        year = mapping.IntegerField(),
                        month = mapping.IntegerField(),
                        day = mapping.IntegerField(),

                        # and musicbrainz metadata
                        mb_artist_id = mapping.TextField(),
                        mb_track_id = mapping.TextField(),
                        mb_album_id = mapping.TextField(),
                        mb_album_artist_id = mapping.TextField(),
                    )),
            ))),

            # each fragment shares some properties
            samplerate = mapping.IntegerField(),
            duration = mapping.IntegerField(),
            # FIXME: this would be different for different encodings ?
            audio_md5sum = mapping.TextField(),

            # fingerprints
            chroma = mapping.DictField(mapping.Mapping.build(
                    chromaprint = mapping.TextField(),
                    duration = mapping.TextField(),
                    # looked up on musicbrainz
                    mbid = mapping.TextField(),
                    artist = mapping.TextField(),
                    title = mapping.TextField(),
                    lookedup = mapping.DateTimeField(),
            )),


            # fragment info
            start = mapping.LongField(), # in samples
            end = mapping.LongField(), # in samples
            peak = mapping.FloatField(),
            rms = mapping.FloatField(),
            rms_percentile = mapping.FloatField(),
            rms_peak = mapping.FloatField(),
            rms_weighted = mapping.FloatField(),
            attack = mapping.ListField(mapping.TupleField((
                mapping.FloatField, mapping.LongField))),
            decay = mapping.ListField(mapping.TupleField((
                mapping.FloatField, mapping.LongField)))
        ))
    )

    def addFragment(self, host, path, md5sum=None, metadata=None):
        md = {}

        if metadata:
            # FIXME: better way to get fields ?
            for field in Track.fragments.field.mapping.files.field.mapping.metadata.mapping._fields.keys():
                parts = field.split('_')
                for i, part in enumerate(parts[1:], start=1):
                    parts[i] = part[0].upper() + part[1:]
                camel = ''.join(parts)
                md[field] = getattr(metadata, camel)

            print md

        files = []
        self.filesAppend(files, host, path, md5sum, metadata)
        fragment = {
            'files': files
        }

        self.fragments.append(fragment)

    def filesAppend(self, files, host, path, md5sum=None, metadata=None):
        md = {}

        if metadata:
            # FIXME: better way to get fields ?
            for field in Track.fragments.field.mapping.files.field.mapping.metadata.mapping._fields.keys():
                parts = field.split('_')
                for i, part in enumerate(parts[1:], start=1):
                    parts[i] = part[0].upper() + part[1:]
                camel = ''.join(parts)
                md[field] = getattr(metadata, camel)

            print md

        files.append({
            'host': host,
            'path': path,
            'md5sum': md5sum,
            'metadata': md,
            })


# old documents
class Category(mapping.Document):
    type = mapping.TextField(default="category")

    name = mapping.TextField()

class User(mapping.Document):
    type = mapping.TextField(default="user")

    name = mapping.TextField()

class Score(mapping.Document):
    # scores for an object from a single person for various categories
    type = mapping.TextField(default="score")

    user_id = mapping.TextField()
    
    subject_type = mapping.TextField() # what are we scoring ?
    subject_id = mapping.TextField() # which one are we scoring ?

    scores = mapping.ListField(
        mapping.DictField(mapping.Mapping.build(
            category_id = mapping.TextField(),
            score = mapping.FloatField(), # between 0.0 and 1.0
    )))

class Artist(mapping.Document):
    type = mapping.TextField(default="artist")

    name = mapping.TextField()
    sortname = mapping.TextField()
    displayname = mapping.TextField()

    added = mapping.DateTimeField(default=datetime.datetime.now)
    # FIXME: timestamp

class Album(mapping.Document):
    type = mapping.TextField(default="album")

    name = mapping.TextField()
    artist_ids = mapping.ListField(mapping.TextField())

    added = mapping.DateTimeField(default=datetime.datetime.now)

class File(mapping.Document):
    type = mapping.TextField(default="file")

    directory_id = mapping.TextField()

    name = mapping.TextField()
    mtime = mapping.DateTimeField()
    size = mapping.IntegerField()
    md5sum = mapping.TextField()

class AudioFile(File):
    type = mapping.TextField(default="audiofile")

    samplerate = mapping.IntegerField()
    duration = mapping.IntegerField()
    audio_md5sum = mapping.TextField()

class Volume(mapping.Document):
    """
    I am a storage area for files that can be attached or removed to a
    computer.

    My name is unique.
    """
    type = mapping.TextField(default="volume")

    name = mapping.TextField()
    path = mapping.TextField()

    def __repr__(self):
        return "<Volume %s>" % self.name

    def __unicode__(self):
        return self.name

class Directory(mapping.Document):
    """
    I am a directory in which audio files live.
    I either am the child of a volume, or of a parent directory.

    I have a unique name under my parent/volume.
    """
    type = mapping.TextField(default="directory")

    name = mapping.TextField()

    volume_id = mapping.TextField()
    # directory id; can be None if parent is volume
    parent_id = mapping.TextField() 

    mtime = mapping.DateTimeField()
    inode = mapping.IntegerField()

class OldTrack(mapping.Document):
    type = mapping.TextField(default="track")

    name = mapping.TextField()

    artist_ids = mapping.ListField(mapping.TextField())

    added = mapping.DateTimeField(default=datetime.datetime.now)

# FIXME: maybe this should go on an album instead ?
class TrackAlbum(mapping.Document):
    """
    I am an association between tracks and the albums they're on.
    """
    type = mapping.TextField(default="trackalbum")

    track_id = mapping.TextField()
    album_id = mapping.TextField()

    number = mapping.IntegerField()

class Score(mapping.Document):
    type = mapping.TextField(default="score")

    subject_id = mapping.TextField()
    subject_type = mapping.TextField()
    # FIXME: category_id should go here ?
    category_id = mapping.TextField()
    user_id = mapping.TextField()
    scores = mapping.ListField(mapping.DictField(mapping.Mapping.build(
        category_id=mapping.TextField(),
        score=mapping.FloatField())))
    added = mapping.DateTimeField(default=datetime.datetime.now)

class Slice(mapping.Document):
    type = mapping.TextField(default="slice")

    audiofile_id = mapping.TextField()
    track_id = mapping.TextField()

    start = mapping.LongField() # in samples
    end = mapping.LongField() # in samples
    peak = mapping.FloatField()
    rms = mapping.FloatField()
    rms_percentile = mapping.FloatField()
    rms_peak = mapping.FloatField()
    rms_weighted = mapping.FloatField()
    attack = mapping.ListField(mapping.TupleField((
        mapping.FloatField, mapping.LongField)))
    decay = mapping.ListField(mapping.TupleField((
        mapping.FloatField, mapping.LongField)))
