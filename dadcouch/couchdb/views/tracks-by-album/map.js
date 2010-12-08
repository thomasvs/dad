function(doc) {
    if (doc.type == 'album') {
        emit([doc._id, 0], doc);
    }
    else if (doc.type == 'trackalbum') {
        emit([doc.album_id, 1], doc.track_id);
    }
}
