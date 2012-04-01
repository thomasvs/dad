// For each track
//   for each artist
//     emit
//       key artist mid
//       value:
//         name
//         sortname
//         id
//         mbid

// !code lib/dad/track.js




function emitRow(name, sortname, id, mid, mbid, docid) {
    emit(mid, {
        'name': name,
        'sortname': sortname,
        'id': id,
        'mid': mid,
        'mbid': mbid,
        'trackId': docid
    });
}

function(doc) {
    if (doc.type == 'track') {
        var artistList = track.getArtists(doc);

        artistList.forEach(
            function(artist) {
                emitRow(artist.name, artist.sortname, artist.id, track.getArtistMid(artist), artist.mbid, doc._id);
            }
        );
    }
}
