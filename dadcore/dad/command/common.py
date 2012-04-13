# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

"""
Helper functionality for the command line application.
"""

import os

def expandPaths(paths, stderr=None):
    """
    @param paths: iteratable of str

    @rtype: generator of C{unicode}
    """
    for path in paths:
        try:
            path = path.decode('utf-8')
        except UnicodeDecodeError, e:
            stderr.write('Invalid path %r, skipping\n' % path)
            continue

        if not os.path.exists(path):
            stderr.write('Could not find %s\n' % path.encode('utf-8'))
            continue

        # handle playlist
        if path.endswith('.m3u'):
            handle = open(path, 'r')
            for line in handle.readlines():
                if line.startswith('#'):
                    continue
                filePath = line.decode('utf-8').strip()
                # FIXME: handle relative paths here
                if not os.path.exists(filePath):
                    stderr.write('Could not find %s\n' %
                        filePath.encode('utf-8'))
                    continue
                yield filePath
        else:
            yield path
