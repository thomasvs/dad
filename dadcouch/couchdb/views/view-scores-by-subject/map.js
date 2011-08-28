// for each score, emit subject of score
function(doc) {

    if (doc.scores) {
        doc.scores.forEach(
            function(score) {
    	        emit(doc._id, [score.user, score.category, score.score]);
            }
        )
    }
}
