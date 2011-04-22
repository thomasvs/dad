// for each score, emit subject of score
function(doc) {
    if (doc.type == 'score') {
    	emit(doc.subject_id, null);
    }
}
