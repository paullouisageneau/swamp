"""
    Copyright (C) 2017 by Paul-Louis Ageneau
    paul-louis (at) ageneau (dot) org

    This file is part of Swamp.

    Swamp is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    Swamp is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with Swamp.
    If not, see <http://www.gnu.org/licenses/>.
"""

import re


class Parser:
    PatternVideoExt = "mkv|mp4|avi"
    PatternAudioExt = "mp3|m4a|ogg|flac"

    PatternSerie = re.compile(r"(?:\[(.*)\]\.?)?([^\[\]]+)(?:\.|\-)(?:S([0-9]{2}) ?E([0-9]{2})|([0-9]{1,2})X([0-9]{2}))(?:(?:\.|\-)(.*))?\.(" + PatternVideoExt + ")$", re.IGNORECASE)
    PatternMovie = re.compile(r"(?:\[(.*)\]\.?)?([^\[\]]+)(?:\.|\-)(\(?((?:19|20)[0-9]{2})\)?)(?:(?:\.|\-)(.*))?\.(" + PatternVideoExt + ")$", re.IGNORECASE)
    PatternMusic = re.compile(r"(?:\[(.*)\]\.?)?(?:([0-9]{1,3})(?:\-|\.))?(?:(.+[^0-9])\-)?(?:([0-9]{1,3})\-)?([^()]+)(?:\.\((.*)\))?\.(" + PatternAudioExt + ")$", re.IGNORECASE)

    def __init__(self, filename):
        self.type = 0
        self.name = ""

        # Clean filename
        cfilename = filename.replace("_", " ")
        cfilename = re.sub(r"[\. ]+", r".", cfilename)
        cfilename = re.sub(r"\.*\-+\.*", r"-", cfilename)

        # Match
        m = Parser.PatternSerie.match(cfilename)
        if m:
            self.type = 1
            self.tag = m.group(1) or ""
            self.title = m.group(2).replace(".", " ").title()
            self.season = int(m.group(3) or m.group(5) or "0")
            self.episode = int(m.group(4) or m.group(6) or "0")
            self.name = "{} S{:02d}E{:02d}".format(self.title, self.season, self.episode)
            print(
                "Serie: " + self.title
                + ("\tseason=" + str(self.season))
                + ("\tepisode=" + str(self.episode))
                + ("\ttag = " + self.tag if self.tag else "")
            )
            return

        m = Parser.PatternMovie.match(cfilename)
        if m:
            self.type = 2
            self.tag = m.group(1)
            self.title = m.group(2).replace(".", " ").title()
            self.name = self.title
            print(
                    "Movie: " + self.title
                    + ("\ttag = " + self.tag if self.tag else "")
            )
            return

        m = Parser.PatternMusic.match(cfilename)
        if m:
            self.type = 3
            self.tag = m.group(1) or ""
            self.track = int(m.group(2) or m.group(4) or "0")
            self.artist = (m.group(3) or "").replace(".", " ").title()
            self.title = m.group(5).replace(".", " ").title()
            self.name = (self.artist + ", " if self.artist else "") + self.title
            if self.track or self.artist:
                print(
                    "Music: " + self.title
                    + ("\ttrack=" + str(self.track) if self.track > 0 else "")
                    + ("\tartist=" + self.artist if self.artist else "")
                    + ("\ttag = " + self.tag if self.tag else "")
                )
                return
