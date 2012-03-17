# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base implementation of common database methods.
"""

from twisted.internet import defer

from dad.model import scorable, track
from dad.common import log

class Database(log.Loggable):
    """
    Base class for database.
    """
    @defer.inlineCallbacks
    def score(self, model, userName, categoryName, score):
        """
        Score the given model.
        Recalculates track scores if needed.
        """
        assert isinstance(model, scorable.ScorableModel), \
            "Cannot score %r" % model
        self.debug('score: model %r', model)
        yield model.setScore(userName, categoryName, score)

        if isinstance(model, track.TrackModel):
            yield self.recalculateTrackScore(model)
            return

        # artists and albums
        tracks = yield model.getTracks()
        tracks = list(tracks)
        self.debug('recalculating score on %d tracks', len(tracks))
        for t in tracks:
            self.debug('score: model %r: recalculating on track %r',
                model, t)
            yield self.recalculateTrackScore(t)
        self.debug('recalculated score on %d tracks', len(tracks))

    @defer.inlineCallbacks
    def recalculateTrackScore(self, tm):
        """
        Recalculate the aggregate track score of a track, taking into account
        artist and album scores.

        @type  tm: L{dad.model.track.TrackModel}
        """
        def _calculate(track, artists, albums):
            """
            Calculate an aggregate score given the inputs.
            """
            self.debug('based on %r track, %r artists, %r albums',
                track, artists, albums)

            typed = []

            if track:
                typed.append(track)
            if artists:
                typed.append(_geometric(artists))
            if albums:
                typed.append(_geometric(albums))
            return _geometric(typed)

        def _geometric(values):
            product = 1.0
            for v in values:
                product *= v
            return pow(product, 1.0 / len(values))

        pairs = {}
        scores = {}

        trackScores = yield tm.getScores()
        for score in trackScores:
            scores[tm] = score
            key = (score.user, score.category)
            if not key in pairs:
                pairs[key] = []
            pairs[key].append((score.score, 'track'))

        artists = yield tm.getArtists()
        for artist in artists:
            artistScores = yield artist.getScores()
            for score in artistScores:
                scores[artist] = score
                key = (score.user, score.category)
                if not key in pairs:
                    pairs[key] = []
                pairs[key].append((score.score, 'artist'))
        
        for ((user, category), scoreModels) in pairs.items():
            track = None
            artists = []

            for value, which in scoreModels:
                if which == 'track':
                    track = value
                elif which == 'artist':
                    artists.append(value)

            value = _calculate(track, artists, [])
            self.debug('Setting score on %r to %r, %r, %r',
                tm, user, category, value)
            tm = yield tm.setCalculatedScore(user, category, value)
