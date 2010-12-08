function(doc) {
    if (doc.type == 'slice') {
        emit([doc.track_id, doc.audiofile_id, doc.start, doc.end], 1);
    }
}
