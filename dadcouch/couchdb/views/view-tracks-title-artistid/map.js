// For each track, emit
// key: title
// value: tuple of artist name/sortname/id/mbid, album name/sortname/id/mbid

// !code lib/dad/track.js

function(doc) {

    if (doc.type == 'track') {
        // FIXME: update as well in view-albums-by-artist
        var artistList = track.getArtists(doc);
        var albumList = track.getAlbums(doc);
        var titles = track.getTitles(doc);

        titles.forEach(
            function(title) {
                emit(title, [artistList, albumList]);
            }
        );
    }
}
