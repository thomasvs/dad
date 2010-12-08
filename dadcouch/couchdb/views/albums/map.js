function(doc) {
    if (doc.type == 'album') {
        emit(doc.name, 1);
    }
}
