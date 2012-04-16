# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import itertools

# see
# http://stackoverflow.com/questions/243865/how-do-i-merge-two-python-iterators
# gets one from each iterator in the list
def tmerge(*iterators):
    empty = {}

    for values in itertools.izip_longest(*iterators, fillvalue=empty):
        for value in values:
            if value is not empty:
                yield value
