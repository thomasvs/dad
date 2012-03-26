# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Base classes for model/view/controller.
"""

from dad.base import base

class BackedModel(base.Model):
    """
    I hold data coming from a database.
    """

    def __init__(self, database):
        """
        @type  database: L{dad.base.database.Database}
        """
        # import here to avoid circular import
        from dad.base import database as db
        assert isinstance(database, db.Database)
        self.database = database

    def getOrCreate(self):
        """
        Look up a database-backed model, or create a new one.

        The returned model can then be changed and saved to the database.

        @rtype: instance of subclass of L{BackedModel}
        """
        raise NotImplementedError, '%r does not implement getOrCreate' % self.__class__


class ScorableModel(BackedModel):
    """
    I am a base class for models that can be given scores.
    """

    subjectType = 'none'

    def getCategories(self):
        """
        @returns: deferred firing generator of category names.
        """
        raise NotImplementedError

    def getScores(self, userName=None):
        """
        Get a subject's scores.

        @rtype: deferred firing generator of user, category, score
        """
        raise NotImplementedError

    def setScore(self, userName, categoryName, score):
        """
        Score a subject directly.
        """
        raise NotImplementedError

    def score(self, userName, categoryName, score):
        """
        Score a subject and possibly recalculate internal scoring.
        """
        raise NotImplementedError


# FIXME: decide on snake case vs camelCase
class SelectorView(base.View):
    """
    I am a base class for selector widgets.
    """
    title = 'Selector, override me'

    def add_row(self, item, display, sort, tracks):
        """
        @param item:    an item that can serve as a model for an individual
                        item view
        @param display: the display name of the item
        @type  display: C{unicode}
        @type  sort:    C{unicode}
        @param tracks:  the number of tracks
        @type  tracks:  int
        """
        raise NotImplementedError

    def throb(self, active=True):
        """
        Start or stop throbbing the selector to indicate activity.

        @param active: whether to throb
        """
        pass
