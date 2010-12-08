// for each track score, emit category_id/user_id/track_id and score
function(doc) {
    if (doc.type == 'score' && doc.subject_type == 'track') {
        doc.scores.forEach(
            function(d) {
                emit([d.category_id, doc.user_id, doc.subject_id], d.score);
            }
        )
    }
}
