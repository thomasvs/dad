function(doc) {
    if (doc.type == 'audiofile') {
        emit([doc.name, doc.directory_id], 1);
    }
}
