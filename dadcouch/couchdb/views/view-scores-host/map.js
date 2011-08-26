// for each score on a track
// key:   [user, category, score, user]
// value: [hosts] on which this track is available
function(doc) {
    if (doc.type == 'track' && doc.scores) {

        var hosts = [];

        doc.fragments.forEach(
            function(fragment) {
                fragment.files.forEach(
                    function(file) {
                        if (!(file.host in hosts)) {
                            hosts.push(file.host);
                        }
                    }
                );
            }
        );
        doc.scores.forEach(
            function(score) {
    	        emit([score.user, score.category, score.score], hosts);
            }
        );
    }
}
