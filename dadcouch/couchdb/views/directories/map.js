function(doc) {
    if (doc.type == 'directory') {
        emit(doc.name, 1);
    }
}
