function(doc) {
    if (doc.type == 'selection') {
        emit(doc.name, 1);
    }
}
