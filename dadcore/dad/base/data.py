# -*- Mode: Python; test-case-name: dad.test.test_base_data -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes for data exchange.
"""

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
