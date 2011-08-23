// For each album, emit the artist
function(doc) {
    if (doc.type == 'track') {
	    // first, collect all artists
	    var artists = {};

        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    artists[artist.name] = [artist.name, artist.sortname, artist.id];
                }
            )
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.artist) {
                                        // FIXME: for now we emit artist as id, but maybe we should do null and adapt the code ?
                                    artists[file.metadata.artist] = [file.metadata.artist, file.metadata.artist, file.metadata.artist];
                                }
                            }
                        )
                    }
                )
            }
        }

        // now, emit for each album
        for (var artist in artists) {
            if (doc.albums && doc.albums.length > 0) {
                doc.albums.forEach(
                    function(album) {
                        a = artists[artist]

                        emit([a[0], a[1], a[2], album.name, album.sortname, album.id], 1);
                    }
                )
            } else {
                if (doc.fragments) {
                    doc.fragments.forEach(
                        function(fragment) {
                            fragment.files.forEach(
                                function(file) {
                                    if (file.metadata && file.metadata.album) {
                                            // FIXME: for now we emit album as id, but maybe we should do null and adapt the code ?
                        a = artists[artist]

                        emit([a[0], a[1], a[2], file.metadata.album, file.metadata.album, file.metadata.album], 1);
                                    }
                                }
                            )
                        }
                    )
                }
            }
        }
    }
}
