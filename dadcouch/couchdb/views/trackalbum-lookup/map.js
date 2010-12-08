function(doc) {
    if (doc.type == 'trackalbum') {
        emit([doc.track_id, doc.album_id, doc.number], 1);
    }
}
