// For each track
//   for each album
//     emit
//       key album mid
//       value:
//         name
//         sortname
//         id
//         mbid

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

function emitRow(name, sortname, id, mid, mbid, docid) {
    emit(mid, {
        'name': name,
        'sortname': sortname,
        'id': id,
        'mid': mid,
        'mbid': mbid,
        'trackId': docid
    });
}

function(doc) {
    var seen = {}

    if (doc.type == 'track') {
        if (doc.albums && doc.albums.length > 0) {
            doc.albums.forEach(
                function(album) {
                    emitRow(album.name, album.sortname, album.id, getAlbumMid(album), album.mbid, doc._id);
                    seen[album.name] = 1;
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
                                    if (!(file.metadata.album in seen)) {
                                        // FIXME: for now we emit album as id, but maybe we should do null and adapt the code ?
                                        aid = getMetadataAlbumMid(file.metadata);
                                        if (aid) {
                                            emitRow(file.metadata.album, file.metadata.album, null, aid, file.metadata.mb_album_id, doc._id);

                                            seen[file.metadata.album] = 1;
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
