// For each artist document, emit lookup aid's

function(doc) {
    if (doc.type == 'artist') {
        if (doc.name) {
            emit('artist:name:' + doc.name, 1);
        }
        if (doc.mbid) {
            emit('artist:mbid:' + doc.mbid, 1);
        }
}
