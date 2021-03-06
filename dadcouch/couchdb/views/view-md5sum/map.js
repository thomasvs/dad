// For each track, emit all different md5sums as key
// and the track id as value
function(doc) {
    var seen = {};

    if (doc.type == 'track') {
        doc.fragments.forEach(
            function(fragment) {
                fragment.files.forEach(
                    function(file) {
                        if (!(file.md5sum in seen)) {
                            emit(file.md5sum, doc._id);
                            seen[file.md5sum] = 1;
                        }
                    }
                )
            }
        )
    }
}
