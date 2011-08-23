# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import datetime
import math

from dad.model import track

from dadcouch.extern.paisley import mapping

"""
Document mappings from CouchDB to python.
"""


# new documents
class Track(mapping.Document, track.TrackModel):
    type = mapping.TextField(default="track")

    name = mapping.TextField()

    artists = mapping.ListField(
        mapping.DictField(mapping.Mapping.build(
            name = mapping.TextField(),
            sortname = mapping.TextField(),
            id = mapping.TextField())))

    albums = mapping.ListField(
        mapping.DictField(mapping.Mapping.build(
            name = mapping.TextField(),
            sortname = mapping.TextField(),
            id = mapping.TextField(),
            number = mapping.IntegerField(),
            # tracks can be fragments of album numbers, so count them
            fragment = mapping.IntegerField(),
    )))


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
                    # volume = mapping.TextField(),
                    # volume_path = mapping.TextField(),
                    path = mapping.TextField(),
                    md5sum = mapping.TextField(),
                    mtime = mapping.DateTimeField(),
                    device = mapping.IntegerField(),
                    inode = mapping.IntegerField(),
                    size = mapping.IntegerField(),

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

                        # and stream info
                        length = mapping.IntegerField(), # in samples
                    )),

                    # the fragment number in this file
                    number = mapping.IntegerField(),
            ))),

            # each fragment shares some properties
            rate = mapping.IntegerField(),
            channels = mapping.IntegerField(),
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


            # fragment level info
            level = mapping.DictField(mapping.Mapping.build(
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
        ))
    )
    # scores given by users to this track
    scores = mapping.ListField(
        mapping.DictField(mapping.Mapping.build(
            user = mapping.TextField(),
            category = mapping.TextField(),
            score = mapping.FloatField(), # between 0.0 and 1.0
        ))
     )
    # scores calculated from track/artist/album
    calculated_scores = mapping.ListField(
        mapping.DictField(mapping.Mapping.build(
            user = mapping.TextField(),
            category = mapping.TextField(),
            score = mapping.FloatField(), # between 0.0 and 1.0
        ))
    )
 
    def _camelCaseFields(self, fieldName):
        """
        Return camel case variant of dashed field names.
        """
        parts = fieldName.split('_')
        for i, part in enumerate(parts[1:], start=1):
            parts[i] = part[0].upper() + part[1:]
        camel = ''.join(parts)

        return camel
 
    def addFragment(self, info, metadata=None, mix=None, number=None):
        files = []
        self.filesAppend(files, info, metadata, number)
        fragment = {
            'files': files,
        }
        if metadata:
            fragment.update({
                'channels': metadata.channels,
                'rate': metadata.rate,
            })

        if mix:
            self.fragmentSetMix(fragment, mix)

        self.fragments.append(fragment)


    def filesAppend(self, files, info, metadata=None, number=None):
        md = {}

        if metadata:
            # FIXME: better way to get fields ?
            for field in Track.fragments.field.mapping.files.field.mapping.metadata.mapping._fields.keys():
                camel = self._camelCaseFields(field)
                md[field] = getattr(metadata, camel)


        d = {
            'host':     info.host,
            'path':     info.path,
            'md5sum':   info.md5sum,
            'device':   info.device,
            'inode':    info.inode,
            'size':     info.size,

            'metadata': md,
        }
        if info.mtime:
            d['mtime'] = datetime.datetime.fromtimestamp(info.mtime)
        if number:
            d['number'] = number

        files.append(d)


    def fragmentSetMix(self, fragment, mix):
        m = {}

        for key in [
            'start', 'end', 'peak', 'rms',
            'rms_percentile', 'rms_peak', 'rms_weighted', 'attack', 'decay']:
            camel = self._camelCaseFields(key)
            m[key] = getattr(mix, camel)

        fragment['level'] = m

    def getArtists(self):
        if self.artists:
            return self.artists

        # FIXME: better ? faster ? stronger ?
        if not self.fragments:
            return
        if not self.fragments[0].files:
            return
        if not self.fragments[0].files[0].metadata:
            return
        if not self.fragments[0].files[0].metadata.artist:
            return

        return [self.fragments[0].files[0].metadata.artist, ]

    def getName(self):
        if self.name:
            return self.name

        # FIXME: better ? faster ? stronger ?
        if not self.fragments:
            return
        if not self.fragments[0].files:
            return
        if not self.fragments[0].files[0].metadata:
            return
        return self.fragments[0].files[0].metadata.title


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
