// For each track, emit
// key: title
// value: list of artist ids
function(doc) {
    if (doc.type == 'track') {
        var seen = {};
	    var artists = {};
	    var albums = {};

        // FIXME: copied from view-albums-by-artist, share somehow ?
        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    artists[artist.name] = {
                        'name': artist.name,
                        'sortname': artist.sortname,
                        'id': artist.id,
                        'mbid': artist.mbid,
                    };
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
                                    artists[file.metadata.artist] = {
                                        'name': file.metadata.artist,
                                        'sortname': file.metadata.artist,
                                        'id': null,
                                        'mbid': file.metadata.mb_artist_id,
                                    };
                                }
                            }
                        );
                    }
                );
            }
        }

        if (doc.albums && doc.albums.length > 0) {
            doc.albums.forEach(
                function(album) {
                    albums[album.name] = {
                        'name': album.name,
                        'sortname': album.sortname,
                        'id': album.id,
                        'mbid': album.mbid,
                    };
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
                                    albums[file.metadata.album] = {
                                        'name': file.metadata.album,
                                        'sortname': file.metadata.album,
                                        'id': null,
                                        'mbid': file.metadata.mb_album_id,
                                    };
                                }
                            }
                        );
                    }
                );
            }
        }


        var artistList = [];
        for (var artist in artists) {
            artistList.push(artists[artist]);
        }

        var albumList = [];
        for (var album in albums) {
            albumList.push(albums[album]);
        }


        if (doc.name) {
            emit (doc.name, [artistList, albumList]);
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.title) {
                                    if (!(file.metadata.title in seen)) {
                                        emit(file.metadata.title, [artistList, albumList]);
                                        seen[file.metadata.title] = 1;
                                    }
                                }
                            }
                        );
                    }
                );
            }

        }
    }
}
