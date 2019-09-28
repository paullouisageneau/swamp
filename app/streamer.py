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

import subprocess
import os.path
import re

directory = "/home/public"


class Streamer:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.isfile(filename):
            raise Exception("File does not exist: " + filename)

    def getDescription(self):
        args = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            self.filename,
        ]
        out = subprocess.check_output(args, shell=False)
        duration = float(out)
        return {"duration": duration}

    def getWebmStream(self, hd=False, start=None, stop=None):
        filters = []
        if hd:
            filters += [r"scale=-1:min(ih*1920/iw\,1080)"]
            filters += [r"pad=1920:1080:(1920-iw)/2:(1080-ih)/2:black"]

        if re.match("^[^\"'\\[\\]]+$", self.filename):
            srt = os.path.splitext(self.filename)[0] + ".srt"
            if os.path.isfile(srt):
                filters += ["subtitles=" + srt + ":charenc=CP1252"]
            elif (
                "codec_type=subtitle"
                in subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_streams", self.filename]
                ).decode()
            ):
                filters += ["subtitles=" + self.filename]

        args = ["ffmpeg"]
        if start:
            args += ["-ss", start]
        args += ["-i", self.filename]
        if stop:
            args += ["-to", stop]
        if len(filters):
            args += ["-vf", ",".join(filters)]
        args += [
            "-v", "error",
            "-copyts",
            "-c:v", "libvpx",
            "-b:v", "4M",
            "-crf", "16",
            "-quality", "realtime",
            "-cpu-used", "8",
            "-c:a", "libvorbis",
            "-ac", "2",
            "-ar", "44100",
            "-f", "webm",
            "-",
        ]

        proc = subprocess.Popen(args, stdin=None, stdout=subprocess.PIPE, shell=False)
        return proc.stdout
