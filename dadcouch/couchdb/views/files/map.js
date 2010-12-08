function(doc) {
    if (doc.type == 'file') {
        emit(doc.name, 1);
    }
}
