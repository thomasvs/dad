// convert doc.artist member to an object with name/sortname/id/mbid/mid

function getArtistMid(artist) {
    mid = null;

    if (artist.id) {
        mid = artist.id;
    } else if (artist.mbid) {
        mid = 'artist:mbid:' + artist.mbid;
    } else if (artist.name) {
        mid = 'artist:name:' + artist.name;
    }

    return mid;
}

function getMetadataArtistMid(metadata) {
    mid = null;

    if (metadata) {
        if (metadata.mb_artist_id) {
            mid = 'artist:mbid:' + metadata.mb_artist_id;
        } else if (metadata.artist) {
            mid = 'artist:name:' + metadata.artist;
        }
    }

    return mid;
}

function getAlbumMid(album) {
    mid = null;

    if (album.id) {
        mid = album.id;
    } else if (album.mbid) {
        mid = 'album:mbid:' + album.mbid;
    } else if (album.name) {
        mid = 'album:name:' + album.name;
    }

    return mid;
}

function getMetadataAlbumMid(metadata) {
    mid = null;

    if (metadata) {
        if (metadata.mb_album_id) {
            mid = 'album:mbid:' + metadata.mb_album_id;
        } else if (metadata.album) {
            mid = 'album:name:' + metadata.album;
        }
    }

    return mid;
}

function getAlbumFromTrackAlbum(album) {
    var o = {};

    o.name = album.name;
    o.sortname = album.sortname;
    o.id = album.id;
    o.mbid = album.mbid;

    o.mid = getAlbumMid(album);

    return o;
}

function getArtistFromTrackArtist(artist) {
    var o = {};

    o.name = artist.name;
    o.sortname = artist.sortname;
    o.id = artist.id;
    o.mbid = artist.mbid;

    o.mid = getArtistMid(artist);

    return o;
}

function getArtistFromMetadata(metadata) {
    var o = {};

    o.name = metadata.artist;
    o.sortname = metadata.artist;
    o.id = null;
    o.mbid = metadata.mb_artist_id;

    o.mid = getMetadataArtistMid(metadata);

    return o;
}

function getAlbumFromMetadata(metadata) {
    var o = {};

    o.name = metadata.album;
    o.sortname = metadata.album;
    o.id = null;
    o.mbid = metadata.mb_album_id;

    o.mid = getMetadataAlbumMid(metadata);

    return o;
}

// FIXME: should getArtistFromTrackArtist be on doc instead too ?
function getArtistsFromChroma(chroma) {
    var artists = [];

    if (!chroma.artists) return artists;

    chroma.artists.forEach(
        function(artist) {

            var o = {};

            o.name = artist.name;
            o.sortname = artist.name;
            o.id = null;
            o.mbid = artist.mbid;

            o.mid = 'artist:mbid:' + o.mbid;

            artists.push(o);
        }
    );

    return artists;
}
var track = {

    getArtistMid: getArtistMid,
    getMetadataArtistMid: getMetadataArtistMid,
    getAlbumMid: getAlbumMid,
    getMetadataAlbumMid: getMetadataAlbumMid,
    getArtistFromMetadata: getArtistFromMetadata,

    // return the artists as a list of dicts with name/sortname/id/mbid
    getArtists: function(doc) {

        var artists = {};

        // FIXME: copied from view-albums-by-artist, share somehow ?
        if (doc.artists && doc.artists.length > 0) {
            doc.artists.forEach(
                function(artist) {
                    a = getArtistFromTrackArtist(artist);
                    artists[a.mid] = a;
                }
            );
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        // chromaprint values take precedence over metadata
                        chromaArtists = getArtistsFromChroma(fragment.chroma);
                        if (chromaArtists && chromaArtists.length > 0) {
                            chromaArtists.forEach(
                                function(artist) {
                                    artists[artist.mid] = artist;
                                }
                            );
                        } else {
                            fragment.files.forEach(
                                function(file) {
                                    if (file.metadata && file.metadata.artist) {
                                        // FIXME: for now we emit artist as id, but maybe we should do null and adapt the code ?
                                        a = getArtistFromMetadata(file.metadata);
                                        artists[a.mid] = a;
                                    }
                                }
                            );
                        }
                    }
                );
            }
        }


        var artistList = [];
        for (var key in artists) {
            artistList.push(artists[key]);
        }

        return artistList;
    },

    getAlbums: function(doc) {


        var albums = {};

        if (doc.albums && doc.albums.length > 0) {
            doc.albums.forEach(
                function(album) {
                    a = getAlbumFromTrackAlbum(album);
                    albums[a.mid] = a;
                }
            );
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.album) {
                                        // FIXME: for now we emit album as id, but maybe we should do null and adapt the code ?
                                    a = getAlbumFromMetadata(file.metadata);
                                    albums[a.mid] = a;
                                }
                            }
                        );
                    }
                );
            }
        }


        var albumList = [];
        for (var album in albums) {
            albumList.push(albums[album]);
        }

        return albumList;
    },

    getTitles: function(doc) {
        var seen = {};
        var titles = [];

        if (doc.name) {
            titles.push(doc.name);
        } else {
            if (doc.fragments) {
                doc.fragments.forEach(
                    function(fragment) {
                        fragment.files.forEach(
                            function(file) {
                                if (file.metadata && file.metadata.title) {
                                    if (!(file.metadata.title in seen)) {
                                        titles.push(file.metadata.title);
                                        seen[file.metadata.title] = 1;
                                    }
                                }
                            }
                        );
                    }
                );
            }

        }

        return titles;
    }

};

// CommonJS bindings
if (typeof(exports) === 'object') {
    exports.getArtists = track.getArtists;
    exports.getAlbums = track.getAlbums;
    exports.getArtistMid = track.getArtistMid;
    exports.getMetadataArtistMid = track.getMetadataArtistMid;
    exports.getAlbumMid = track.getAlbumMid;
    exports.getMetadataAlbumMid = track.getMetadataAlbumMid;
    exports.getArtistFromTrackArtist = track.getArtistFromTrackArtist;
    exports.getArtistFromMetadata = track.getArtistFromMetadata;
}
