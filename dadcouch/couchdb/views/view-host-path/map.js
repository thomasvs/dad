function(doc) {
    if (doc.type == 'track') {
        doc.fragments.forEach(
            function(fragment) {
                fragment.files.forEach(
                    function(file) {
                        emit([file.host, file.path], 1);
                    }
                )
            }
        )
    }
}
