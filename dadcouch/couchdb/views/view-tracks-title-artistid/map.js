// For each track, emit
// key: title
// value: tuple of artist name/sortname/id/mbid, album name/sortname/id/mbid
function(doc) {

    // !code lib/dad/track.js

    if (doc.type == 'track') {
        var artistList = [];
        var albumList = {};
        var titles = [];

        // FIXME: update as well in view-albums-by-artist
        artistList = track.getArtists(doc);
        albumList = track.getAlbums(doc);
        titles = track.getTitles(doc);

        titles.forEach(
            function(title) {
                emit(title, [artistList, albumList]);
            }
        );
    }
}
