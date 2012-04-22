// vi:si:et:sw=4:sts=4:ts=4

// For each track
//   for each different recording musicbrainz id
//     emit
//       key:   recording musicbrainz id
//       value: 1

// !code lib/dad/track.js

function(doc) {
    if (doc.type == 'track') {
        ids = track.getAllMBIds(doc);

        ids.forEach(
            function(id) {
                emit(id, 1);
            }
        );
    }
}
