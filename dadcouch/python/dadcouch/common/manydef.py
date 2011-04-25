# -*- Mode: Python; test_case_name: dadcouch.test.test_common_manydef -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys

from twisted.internet import defer, reactor
from twisted.python import failure

class DeferredListSpaced(defer.Deferred):

    SPACE = 200
    DELAY = 0.0

    def __init__(self, fireOnOneCallback=0, fireOnOneErrback=0,
                 consumeErrors=0):

        defer.Deferred.__init__(self)

        self.resultList = []

        self.fireOnOneCallback = fireOnOneCallback
        self.fireOnOneErrback = fireOnOneErrback
        self.consumeErrors = consumeErrors
        self.finishedCount = 0

        # list of callable, args, kwargs, callbacks
        # where callbacks is list of
        # (cb, cbArgs, cbKWArgs,     def test_DLS(self):
        self._callables = []
        

    def addCallable(self, callable, *args, **kwargs):
        self._callables.append((callable, args, kwargs, []))

    def addCallableCallback(self, callback, *args, **kwargs):
        if self._callables[-1][3] is None:
            self._callables[-1][3] = []

        self._callables[-1][3].append((callback, args, kwargs, None, None, None))

    def addCallableErrback(self, errback, *args, **kwargs):
        if self._callables[-1][3] is None:
            self._callables[-1][3] = []

        self._callables[-1][3].append((None, None, None, errback, args, kwargs))

    def _cbDeferred(self, result, index, succeeded, callbacks):
        self.resultList[index] = (succeeded, result)
        self.finishedCount += 1

        # we call the callbacks before updating internal state and possibly
        # calling back
        if callbacks:
            # FIXME: shouldn't these be chaining ?
            for cb, cbargs, cbkwargs, eb, ebargs, ebkwargs in callbacks:
                if cb and succeeded == defer.SUCCESS:
                    cb(result, *cbargs, **cbkwargs)
                if eb and succeeded == defer.FAILURE:
                    eb(result, *ebargs, **ebkwargs)


        if not self.called:
            if succeeded == defer.SUCCESS and self.fireOnOneCallback:
                self.callback((result, index))
            elif succeeded == defer.FAILURE and self.fireOnOneErrback:
                self.errback(failure.Failure(FirstError(result, index)))
            elif self.finishedCount == len(self.resultList):
                self.callback(self.resultList)

        if succeeded == defer.FAILURE and self.consumeErrors:
            result = None

        if self.DELAY == 0.0:
            return result

        d = defer.Deferred()
        reactor.callLater(self.DELAY, d.callback, result)
        return d
 
    # adds deferred-returning callbacks in a loop at once;
    # this serializes but runs out of stack if count is too high and deferreds
    # return results immediately
    def _blockSerialize(self, index, count):
        # print 'THOMAS: blockSerialize', index, count
        callable, args, kwargs, callbacks = self._callables[index]
        #print 'THOMAS: callable', callable
        #print 'THOMAS: calling with', index, args, kwargs
        #sys.stdout.flush()
        d = defer.maybeDeferred(callable, *args, **kwargs)
        d.addCallbacks(self._cbDeferred, self._cbDeferred,
                       callbackArgs=(index, defer.SUCCESS, callbacks),
                       errbackArgs=(index, defer.FAILURE, callbacks))

        for i in range(index + 1, index + count):
            callable, args, kwargs, callbacks = self._callables[i]
            # print 'THOMAS: deferring with', i, args, kwargs
            sys.stdout.flush()
            # d.addCallback(lambda _, c, a, k: sys.stderr.write(
            #    "callable of %r %r %r\n" % (c, a, k)), callable, args, kwargs)
            d.addCallback(lambda _, c, a, k:
                c(*a, **k), callable, args, kwargs)
            d.addCallbacks(self._cbDeferred, self._cbDeferred,
                           callbackArgs=(i, defer.SUCCESS, callbacks),
                           errbackArgs=(i, defer.FAILURE, callbacks))
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

            reactor.callLater(0, self._blockSerialize, index, left)

            index += left
