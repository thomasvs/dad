# -*- Mode: Python; test-case-name: dad.test.test_audio_common -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# DAD - Digital Audio Database
# Copyright (C) 2008 Thomas Vander Stichele <thomas at apestaart dot org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
Common functions to deal with audio.
"""

import math

def decibelToRaw(decibel):
    """
    Converts a value in decibel to the raw amplitude value.
    """
    return math.pow(10, decibel / 10.0)

def rawToDecibel(raw):
    """
    Converts a raw amplitude value to decibel
    """
    # cheat
    if raw == 0.0:
        return -1000.0
    try:
        return math.log(raw, 10) * 10.0
    except OverflowError:
        raise OverflowError("Cannot take log 10 of %r" % raw)
