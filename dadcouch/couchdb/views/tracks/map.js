function(doc) {
    if (doc.type == 'track') {
        emit(doc.name, 1);
    }
}
