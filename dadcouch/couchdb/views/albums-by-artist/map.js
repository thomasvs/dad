function(doc) {
    if (doc.type == 'artist') {
        emit([doc._id, 0], doc);
    }
    else if (doc.type == 'album') {
        doc.artist_ids.forEach(function(artist_id) {
            emit([artist_id, 1], doc._id);
        });
    }
}
