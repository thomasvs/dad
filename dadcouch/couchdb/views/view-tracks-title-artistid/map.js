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
                        'id': artist.id
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
                                        'id': file.metadata.artist,
                                    };
                                }
                            }
                        );
                    }
                );
            }
        }


        if (doc.name) {
            for (var artist in artists) {
                emit(doc.name, artists[artist]);
            }
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.title) {
                                    if (!(file.metadata.title in seen)) {
                                        for (var artist in artists) {
                                            emit(file.metadata.title, artists[artist]);
                                        }
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
