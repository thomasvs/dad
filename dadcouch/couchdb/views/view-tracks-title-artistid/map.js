// For each track, emit
// key: title
// value: list of artist ids
function(doc) {
    if (doc.type == 'track') {
        var seen = {};
	    var artists = {};

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

        var artistList = [];
        for (var artist in artists) {
            artistList.push(artists[artist]);
        }

        if (doc.name) {
            emit (doc.name, artistList);
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.title) {
                                    if (!(file.metadata.title in seen)) {
                                        emit (file.metadata.title, artistList);
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
