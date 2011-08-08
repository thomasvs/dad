# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# plug-in adding couchdb-based functionality to dad command

import os

from dad.audio import common
from dad.common import logcommand

class Lookup(logcommand.LogCommand):
    description = """Look up audio files in the database."""

    def do(self, args):
        for path in args:
            path = path.decode('utf-8')
            if not os.path.exists(path):
                self.stderr.write('Could not find %s\n' % path.encode('utf-8'))
                continue


            self.stdout.write('%s\n' % path)

# called by main command code before instantiating the class
def plugin(dadCommandClass):
    dadCommandClass.subCommandClasses.append(Lookup)
