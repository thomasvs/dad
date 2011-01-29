function(doc) {
    if (doc.type == 'slice') {
        emit([doc.audiofile_id, doc.start, doc.end], 1);
    }
}
