function(doc) {
    if (doc.type == 'category') {
        emit(doc.name, 1);
    }
}
