function(doc) {
    if (doc.type == 'volume') {
        emit(doc.name, 1);
    }
}
