// For each track, emit all different md5sums as key
// and the track id as value
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
                    }
                )
            }
        )
    }
}
