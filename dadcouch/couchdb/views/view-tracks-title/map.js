// vi:si:et:sw=4:sts=4:ts=4

// For each track, emit the title


function(doc) {
    var seen = {};

    if (doc.type == 'track') {
        if (doc.name) {
            emit(doc.name, 1);
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(

                function(fragment) {
                    if (fragment.chroma && fragment.chroma.title) {
                        if (!(fragment.chroma.title in seen)) {
                            emit(fragment.chroma.title, 1);
                            seen[fragment.chroma.title] = 1;
                        }
                    } else {
                        fragment.files.forEach(

                        function(file) {
                            if (file.metadata && file.metadata.title) {
                                if (!(file.metadata.title in seen)) {
                                    emit(file.metadata.title, 1);
                                    seen[file.metadata.title] = 1;
                                }
                            }
                        });
                    }
                });
            }

        }
    }
}
