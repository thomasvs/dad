# -*- Mode: Python; test-case-name: dad.test.test_database_memory -*-
# vi:si:et:sw=4:sts=4:ts=4

import warnings
warnings.warn("dad.database.memory is deprecated", DeprecationWarning,
    stacklevel=2)

from dad.memorydb.memory import *
from dad.memorydb.model.artist import *
from dad.memorydb.model.track import *
from dad.memorydb.model.album import *
