# -*- Mode: Python; test-case-name: dad.test.test_base_data -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes for data exchange.
"""

class ChromaPrint:
    fingerprint = None
    duration = None # int
    artists = None # list of dict of mbid, name

    metadata = None # Metadata
    mbid = None

    def fromResults(self, results):
        count = {}
        # lists are not hashable, sadly
        artist = {} # repr -> list


        for result in results:
            # highest-scoring result comes first ?
            recordings = result.get('recordings', [])
            for recording in recordings:
                for track in recording.get('tracks', []):
                    artists = track['artists']
                    artist[repr(artists)] = artists
                    key = (recording['id'], repr(artists), track['title'])
                    if not key in count:
                        count[key] = 0
                    count[key] += 1

        frequencies = count.items()
        ordered = sorted(frequencies, key=lambda x: -x[1])

        if not ordered:
            # no results
            return

        mbid, artists, title = ordered[0][0]

        self.metadata = TrackMetadata()
        # FIXME: do we really need metadata here ?
        self.metadata.artists = [a['name'] for a in artist[artists]]

        self.artists = []
        for a in artist[artists]:
            self.artists.append({
                'name': a['name'],
                'mbid': a['id'],
            })
        self.metadata.title = title
        self.mbid = mbid

class TrackMetadata:
    artists = None # list
    title = None

    def __repr__(self):
        return '<TrackMetadata for %s - %s>' % (
            " & ".join([a.encode('utf-8') for a in self.artists]),
            self.title.encode('utf-8'))

class Score:
    """
    I represent a score given to a subject by a user in a category.

    @type  subject:  object
    @type  user:     unicode
    @type  category: unicode
    @ivar  score:    a score between 0.0 and 1.0
    @type  score:    float
    """

    subject = None
    user = None
    category = None
    score = None

    def __repr__(self):
        return "<Score %.3f for user %r in category %r for %r>" % (
            self.score, self.user, self.category, self.subject)
