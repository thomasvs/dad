// For each track
//   for each artist
//     emit
//       key artist mid
//       value:
//         name
//         sortname
//         id
//         mbid

function getArtistMid(artist) {
    mid = null;

    if (artist.id) {
        mid = artist.id;
    } else if (artist.mbid) {
        mid = 'artist:mbid:' + metadata.mb_artist_id;
    } else if (artist.name) {
        mid = 'artist:name:' + metadata.artist;
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

function emitArtist(name, sortname, mid, mbid, docid) {
    emit(mid, {
        'name': name,
        'sortname': sortname,
        'mid': mid,
        'mbid': mbid,
        'trackId': docid
    });
}

function(doc) {
    var seen = {}

    if (doc.type == 'track') {
        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    emitArtist(artist.name, artist.sortname, getArtistMid(artist), artist.mbid, doc._id);
                    seen[artist.name] = 1;
                }
            )
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata) {
                                    // FIXME: seen should be on mid
                                    if (!(file.metadata.artist in seen)) {
                                        // FIXME: for now we emit artist as id, but maybe we should do null and adapt the code ?
                                        aid = getMetadataArtistMid(file.metadata);
                                        if (aid) {
                                            emitArtist(file.metadata.artist, file.metadata.artist, aid, file.metadata.mb_artist_id, doc._id);

                                            seen[file.metadata.artist] = 1;
                                        }
                                    }
                                }
                            }
                        )
                    }
                )
            }

        }
    }
}
