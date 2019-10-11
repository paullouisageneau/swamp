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
    def __init__(self, filename, stream_format="webm"):
        self.filename = filename
        self.stream_format = stream_format
        if not os.path.isfile(filename):
            raise Exception("File does not exist: " + filename)

    def get_description(self):
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

    def get_stream(self, is_hd=False, start=None, stop=None, force_subtitles=False):
        filters = []
        if is_hd:
            filters += [r"scale=-1:min(ih*1920/iw\,1080)"]
            filters += [r"pad=1920:1080:(1920-iw)/2:(1080-ih)/2:black"]

        if re.match("^[^\"'\\[\\]]+$", self.filename):
            srt = os.path.splitext(self.filename)[0] + ".srt"
            if os.path.isfile(srt):
                filters += ["subtitles=" + srt + ":charenc=CP1252"]
            elif force_subtitles and (
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

        if self.stream_format == "webm":
            args += [
                "-c:v", "libvpx",
                "-b:v", "8M" if is_hd else "4M",
                "-crf", "16",
                "-quality", "realtime",
                "-cpu-used", "8",
                "-c:a", "libvorbis",
                "-f", "webm",
            ]
        else:  # matroska
            args += [
                "-c:v", "libx264",
                "-b:v", "8M" if is_hd else "4M",
                "-crf", "26",
                "-preset", "veryfast",
                "-tune", "zerolatency",
                "-movflags", "+faststart",
                "-c:a", "aac",
                "-f", "matroska",
            ]

        args += [
            "-ac", "2",
            "-ar", "48000",
            "-copyts",
            "-v", "error",
            "-",
        ]

        proc = subprocess.Popen(args, stdin=None, stdout=subprocess.PIPE, shell=False)
        return proc.stdout

    @property
    def mimetype(self):
        return "video/{}".format("webm" if self.stream_format == "webm" else "x-matroska")
