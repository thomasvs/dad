// For each track, emit the album
function(doc) {
    var seen = {}

    if (doc.type == 'track') {
        if (doc.albums && doc.albums.length > 0) {
            doc.albums.forEach(
                function(album) {
                    emit([album.name, album.sortname, album.id], doc._id);
                    seen[album.name] = 1;
                }
            )
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.album) {
                                    if (!(file.metadata.album in seen)) {
                                        // FIXME: for now we emit album as id, but maybe we should do null and adapt the code ?
                                        emit([file.metadata.album, file.metadata.album, file.metadata.album],
                                          doc._id);
                                        seen[file.metadata.album] = 1;
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
