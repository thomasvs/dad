// for each score, emit subject of score
function(doc) {
    if (doc.type == 'track' && doc.scores) {
        doc.scores.forEach(
            function(score) {
    	        emit(doc.id, score.user, score.category, score.score);
            }
        )
    }
}
