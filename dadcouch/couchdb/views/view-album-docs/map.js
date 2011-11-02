// For each artist document, emit lookup aid's

function(doc) {
    if (doc.type == 'album') {
        if (doc.name) {
            emit('album:name:' + doc.name, 1);
        }
        if (doc.mbid) {
            emit('album:mbid:' + doc.mbid, 1);
        }
    }
}
