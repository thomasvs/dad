// For each track, emit all artists
function(doc) {
    var seen = {};

    if (doc.type == 'track') {
        if (doc.artists) {
            doc.artists.forEach(
                function(artist) {
                    seen[artist] = 1;
                    emit(artist, 1);
                }
            )
        }

        if (doc.fragments) {
            doc.fragments.forEach(
                function(fragment) {
                    fragment.files.forEach(
                        function(file) {
                            if (file.metadata && file.metadata.artist) {
                                if (!(file.metadata.artist in seen)) {
                                    emit(file.metadata.artist, 1);
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
