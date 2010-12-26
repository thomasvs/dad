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

import unittest

from dad.common import pathscan

class ArtistTest(unittest.TestCase):
    def testOne(self):
        self.assertEquals(pathscan.getPathArtist(
            u'/home/audio/bbq/Broken Social Scene - 13 - Pitter Patter Goes My Heart.mp3'),
            'Broken Social Scene')

    def testTwo(self):
        self.assertEquals(pathscan.getPathArtist(
            u'/path/to/music/Afghan Whigs - Debonair.ogg'),
                'Afghan Whigs')

    def testThree(self):
        self.assertEquals(pathscan.getPathArtist(
            u'/home/audio/bbq/102_Justin_Timberlake_and_Timbaland_-_Sexyback-50K4.mp3'),
            u'Justin Timberlake and Timbaland')

    def testFour(self):
        self.assertEquals(pathscan.getPathArtist(
            u'05 - Clap Your Hands Say Yeah - Details Of The War.mp3'),
            u'Clap Your Hands Say Yeah')
            
    def testFive(self):
        self.assertEquals(pathscan.getPathArtist(
            u'/home/audio/bbq/04. Coldplay - Fix You.mp3'),
            u'Coldplay')
