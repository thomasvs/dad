// For each track, emit all artists
function(doc) {
    if (doc.type == 'track') {
        if (doc.scores) {
            doc.scores.forEach(
                function(score) {
                    emit(score.category, 1);
                }
            )
        }
    }

    if (doc.type == 'category') {
        emit(doc.name, 1);
    }
}
