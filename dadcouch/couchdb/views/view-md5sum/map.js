function(doc) {
    if (doc.type == 'track') {
        doc.fragments.forEach(
            function(fragment) {
                fragment.files.forEach(
                    function(file) {
                        emit(file.md5sum, doc._id);
                    }
                )
            }
        )
    }
}
