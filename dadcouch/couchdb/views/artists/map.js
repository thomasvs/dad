function(doc) {
    if (doc.type == 'artist') {
        emit(doc.name, 1);
    }
}
