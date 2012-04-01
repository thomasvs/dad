// For each track
//   for each artist
//     for each album
//       emit
//       key
//         artist mid
//         dict for artist of name/sortname/id/mid/mbid
//         dict for album of name/sortname/id/mid/mbid
//       value:
//          1

// FIXME: share code between views



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

    // !code lib/dad/track.js
    
    if (doc.type == 'track') {
	    // first, collect all artists
	    var artists = {}; // dict of mid -> name, sort, id, mbid

        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    artists[track.getArtistMid(artist)] = [artist.name, artist.sortname, artist.id, track.getArtistMid(artist), artist.mbid];
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
                                    artists[track.getMetadataArtistMid(file.metadata)] = [file.metadata.artist, file.metadata.artist, null, track.getMetadataArtistMid(file.metadata), file.metadata.mb_artist_id];
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
                            [album.name, album.sortname, album.id, track.getAlbumMid(album), album.mbid]);
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
                            [file.metadata.album, file.metadata.album, null, track.getMetadataAlbumMid(file.metadata), file.metadata.mb_album_id]);
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
