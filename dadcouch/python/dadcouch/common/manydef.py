# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys

from twisted.internet import defer, reactor
from twisted.python import failure

class DeferredListSpaced(defer.Deferred):

    SPACE = 200

    def __init__(self, fireOnOneCallback=0, fireOnOneErrback=0,
                 consumeErrors=0):

        defer.Deferred.__init__(self)

        self.resultList = []

        self.fireOnOneCallback = fireOnOneCallback
        self.fireOnOneErrback = fireOnOneErrback
        self.consumeErrors = consumeErrors
        self.finishedCount = 0

        self._callables = []

    def addCallable(self, callable, *args, **kwargs):
        self._callables.append((callable, args, kwargs))

    def _cbDeferred(self, result, index, succeeded):
        self.resultList[index] = (succeeded, result)
        self.finishedCount += 1

        if not self.called:
            if succeeded == defer.SUCCESS and self.fireOnOneCallback:
                self.callback((result, index))
            elif succeeded == defer.FAILURE and self.fireOnOneErrback:
                self.errback(failure.Failure(FirstError(result, index)))
            elif self.finishedCount == len(self.resultList):
                self.callback(self.resultList)

        if succeeded == defer.FAILURE and self.consumeErrors:
            result = None

        return result
 
    # adds deferred-returning callbacks in a loop at once;
    # this serializes but runs out of stack if count is too high and deferreds
    # return results immediately
    def _blockSerialize(self, index, count):
        print 'THOMAS: blockSerialize', index, count
        callable, args, kwargs = self._callables[index]
        #print 'THOMAS: callable', callable
        #print 'THOMAS: calling with', index, args, kwargs
        #sys.stdout.flush()
        d = defer.maybeDeferred(callable, *args, **kwargs)
        d.addCallbacks(self._cbDeferred, self._cbDeferred,
                       callbackArgs=(index, defer.SUCCESS),
                       errbackArgs=(index, defer.FAILURE))

        for i in range(index + 1, index + count):
            callable, args, kwargs = self._callables[i]
            # print 'THOMAS: deferring with', i, args, kwargs
            sys.stdout.flush()
            # d.addCallback(lambda _, c, a, k: sys.stderr.write(
            #    "callable of %r %r %r\n" % (c, a, k)), callable, args, kwargs)
            d.addCallback(lambda _, c, a, k:
                c(*a, **k), callable, args, kwargs)
            d.addCallbacks(self._cbDeferred, self._cbDeferred,
                           callbackArgs=(i, defer.SUCCESS),
                           errbackArgs=(i, defer.FAILURE))
        return d



    def start(self):
        count = len(self._callables)
        if not count:
            # no deferreds, succeed
            self.callback(self.resultList)

        self.resultList = [None, ] * count

        index = 0
        while count > 0:
            left = count > self.SPACE and self.SPACE or count
            count -= left

            reactor.callLater(0L, self._blockSerialize, index, left)

            index += left
