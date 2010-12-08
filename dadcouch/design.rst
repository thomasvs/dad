Objects
=======

Track
-----

Track is the central object.  A track represents the idea of a single song.
Tracks have a name (the song title) and a list of artists performing it.

A Track contains a link to the artist_ids for this track.

Tracks are not directly linked to an audio file for various reasons:
 * one track can have multiple audio files (single file album,
   hidden bonus tracks)
 * you can know about tracks without having the actual file (shopping list,
   wish list, deleted files)

Audiofile
---------

An audio file is a file containing digital audio data, compressed or
uncompressed.  This data can represent one or more tracks.  The file
can be lossless or lossy.

Audiofiles have a samplerate, duration, and an md5sum calculated on everything
but the metadata.  This can be format- or codec-specific.

Slice
-----

A slice identifies a part of an audio file representing one track.

A slice contains links to:
 * the audiofile it slices
 * the track it represents

It has variables like start and end, as well as audio statistics like
peak, rms, and some special rms parameters used for mixing.

An audio file can have multiple slices; for example:
 * 'All Apologies' on Nirvana's 'In Utero' has 20 minutes of silence
   plus a bonus track
 * 'Swallow' on Placebo's debut album has silence plus a beautiful piano-based
   bonus track.

Artist
------

An artist identifies a performer of tracks/albums/...
It has no links.
It has fields to help in sorting and displaying.

It is linked to by:
 * Track
 * Album

Album
-----

An Album is a collection of tracks.

An Album contains a link to the artist_ids for this album.

An Album does not directly list tracks.  See TrackAlbum.

TrackAlbum
----------

Tracks are not directly linked to an audio file for various reasons:
 * one track can have multiple audio files (single file album,
   hidden bonus tracks)
 * you can know about tracks without having the actual file (shopping list,
   wish list, deleted files)

Directory
---------

A directory in which audio files live.
It has its relative name.

It links to a parent which can be another directory or a volume.

Directories are implemented with relative paths and recursively to make it
easy to

* move directories
* mount volumes in different locations (e.g. same nfs on different machines,
  or a usb disk mounted on different mount points)


Volume
------

A storage volume for audio files and their directories.  It can be attached to
or removed from a computer.

Volumes can theoretically be shared across computers; for example an NFS share.  Maybe we need a VolumeMapping per computer ? They could be mounted on different paths.

Potential denormalizations
==========================

 * put ratings for track/artist/album on the respective documents
 * put slices in track documents


Missing concepts
================

 * Various computers/devices owned
 * their storage locations (some of which might be shared across devices)
 * sync/caching rules
 * playlists

Questions
=========

* What's the best way to query for all tracks that have online audio files ?
* Does it make sense to build aggregate tables on each db update somehow ?
