function(doc) {
    if (doc.type == 'directory') {
        emit([doc.volume_id, doc.parent_id, doc.name], 1);
    }
}
