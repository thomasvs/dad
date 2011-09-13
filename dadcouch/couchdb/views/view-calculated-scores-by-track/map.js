// for each score, emit subject of score
function(doc) {

    if (doc.type == 'track' && doc.calculated_scores) {
        doc.calculated_scores.forEach(
            function(score) {
    	        emit(doc._id, [score.user, score.category, score.score]);
            }
        )
    }
}
