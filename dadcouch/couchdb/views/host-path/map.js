function(doc) {
    if (doc.type == 'track') {
	for (fragment in doc.fragments) {
	    for (file in fragment.files) {
                emit([file.volume_path, file.path], 1);
            }
        }
    }
}
