# -*- Mode: Python; test-case-name: dad.test.test_common_pathscan -*-
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

import os

# FIXME: remove this method
def getPathArtist(path):
    artists, title = parsePath(path)
    return " & ".join(artists)

def parsePath(path):
    # remove extension
    (path, _) = os.path.splitext(path)

    import re
    regexps = [
        # 102_Justin_Timberlake_and_Timbaland_-_Sexyback-50K4.mp3
        # should be before a more generic one
        # start with a track number
        re.compile(r"""^
            (?P<track>\d+)\s*[.-]\s*
            (?P<artist>[^-]*) - 
            (?P<title>.*)""", re.VERBOSE),
        # start with a track number
        re.compile(r"""^
            (?P<track>\d+)
            (?P<artist>[^-]*) - 
            (?P<title>.*)""", re.VERBOSE),
        re.compile(r"""^
            (?P<artist>[^-]*)\s*-\s*
            (?P<track>\d+)\s*-
            (?P<title>.*)"""
            , re.VERBOSE),
        # A-Ha - Crying In The Rain
        re.compile(r"""^
            (?P<artist>.*) - 
            (?P<title>.*)""", re.VERBOSE),
        re.compile(r"""^
            (?P<artist>[^-]*)\s*- 
            (?P<title>.*)""", re.VERBOSE),
    ]

    # get artist from a file path
    basename = os.path.basename(path)

    for regexp in regexps:
        m = regexp.search(basename)
        if m:
            # FIXME: our regexps don't drop the spaces right
            artist = m.group('artist').strip()
            title = m.group('title').strip()
            if not artist and not title:
                continue

            # convert underscore to space
            artist = " ".join(artist.split("_"))

            artist = artist.strip()
            artists = [a.strip() for a in artist.split("&")]
            return artists, title

    return None, None
