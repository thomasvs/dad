// For each track
//   for each artist
//     emit
//       key artist mid
//       value:
//          name
//          sortname
//          id
//          mbid

// FIXME: share code between views


function getArtistMid(artist) {
    mid = null;

    if (artist.id) {
        mid = artist.id;
    } else if (artist.mbid) {
        mid = 'artist:mbid:' + artist.mbid;
    } else if (artist.name) {
        mid = 'artist:name:' + artist.name;
    }

    return mid;
}

function getMetadataArtistMid(metadata) {
    mid = null;

    if (metadata) {
        if (metadata.mb_artist_id) {
            mid = 'artist:mbid:' + metadata.mb_artist_id;
        } else if (metadata.artist) {
            mid = 'artist:name:' + metadata.artist;
        }
    }

    return mid;
}

function getAlbumMid(album) {
    mid = null;

    if (album.id) {
        mid = album.id;
    } else if (album.mbid) {
        mid = 'album:mbid:' + album.mbid;
    } else if (album.name) {
        mid = 'album:name:' + album.name;
    }

    return mid;
}

function getMetadataAlbumMid(metadata) {
    mid = null;

    if (metadata) {
        if (metadata.mb_album_id) {
            mid = 'album:mbid:' + metadata.mb_album_id;
        } else if (metadata.album) {
            mid = 'album:name:' + metadata.album;
        }
    }

    return mid;
}

function emitAlbumArtistRow(mid, artist, album) {
    emit([mid, 
            {
                'name': artist[0],
                'sortname': artist[1],
                'id': artist[2],
                'mid': artist[3],
                'mbid': artist[4],
            },
            {
                'name': album[0],
                'sortname': album[1],
                'id': album[2],
                'mid': album[3],
                'mbid': album[4],
            }], 1);
}

function(doc) {
    if (doc.type == 'track') {
	    // first, collect all artists
	    var artists = {}; // dict of mid -> name, sort, id, mbid

        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    artists[getArtistMid(artist)] = [artist.name, artist.sortname, artist.id, getArtistMid(artist), artist.mbid];
                }
            );
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.artist) {
                                        // FIXME: for now we emit artist as id, but maybe we should do null and adapt the code ?
                                    artists[getMetadataArtistMid(file.metadata)] = [file.metadata.artist, file.metadata.artist, null, getMetadataArtistMid(file.metadata), file.metadata.mb_artist_id];
                                }
                            }
                        );
                    }
                );
            }
        }

        // now, emit for each album
        for (var artist in artists) {
            if (doc.albums && doc.albums.length > 0) {
                doc.albums.forEach(
                    function(album) {
                        a = artists[artist];
                        emitAlbumArtistRow(artist, a,
                            [album.name, album.sortname, album.id, getAlbumMid(album), album.mbid]);
                    }
                );
            } else {
                if (doc.fragments) {
                    doc.fragments.forEach(
                        function(fragment) {
                            fragment.files.forEach(
                                function(file) {
                                    if (file.metadata && file.metadata.album) {
                                            // FIXME: for now we emit album as id, but maybe we should do null and adapt the code ?
                        a = artists[artist];

                        emitAlbumArtistRow(artist, a, 
                            [file.metadata.album, file.metadata.album, null, getMetadataAlbumMid(file.metadata), file.metadata.mb_album_id]);
                                    }
                                }
                            );
                        }
                    );
                }
            }
        }
    }
}
