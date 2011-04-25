function(doc) {
    if (doc.type == 'track') {
        emit(doc.name, doc.artist_ids);
    }
}
