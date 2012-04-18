// vi:si:et:sw=4:sts=4:ts=4

// For each track, emit
// key: mb track id
// value: doc id


function(doc) {
    var seen = {};

    if (doc.type == 'track') {
        doc.fragments.forEach(

        function(fragment) {
            fragment.files.forEach(

            function(file) {
                if (file.metadata && file.metadata.mb_track_id) {
                    if (!(file.metadata.mb_track_id in seen)) {
                        emit(file.metadata.mb_track_id, doc._id);
                        seen[file.metadata.mb_track_id] = 1;
                    }
                }
            });
        });
    }
}
