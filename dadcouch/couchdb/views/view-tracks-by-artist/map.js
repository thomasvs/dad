// For each track, emit the artist
function(doc) {
    var seen = {}

    if (doc.type == 'track') {
        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    emit([artist.name, artist.sortname, artist.id], doc._id);
                    seen[artist.name] = 1;
                }
            )
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.artist) {
                                    if (!(file.metadata.artist in seen)) {
                                        // FIXME: for now we emit artist as id, but maybe we should do null and adapt the code ?
                                        aid = 'artist:name:' + file.metadata.artist;
                                        if (file.metadata.mb_artist_id) {
                                            aid = 'artist:mbid:' + file.metadata.mb_artist_id;
                                        }
                                        emit([file.metadata.artist, file.metadata.artist, aid],
                                          doc._id);
                                        seen[file.metadata.artist] = 1;
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
