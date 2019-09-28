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

import time

ENABLE_CHROMECAST = True
try:
    import pychromecast
except ImportError:
    print("Missing pychromecast package, disabling Chromecast support")
    ENABLE_CHROMECAST = False


def Cast():
    return ChromeCast() if ENABLE_CHROMECAST else None


class ChromeCast:
    def __init__(self):
        self.cast = None

    def list(self):
        return list(map(lambda c: c.device.friendly_name, pychromecast.get_chromecasts()))

    def connect(self, name=None):
        self.disconnect()
        chromecasts = pychromecast.get_chromecasts()
        self.cast = next(
            (c for c in chromecasts if name is None or c.device.friendly_name == name), None
        )
        if self.cast is None:
            raise Exception("Chromecast not found (name={})".format(name))
        self.cast.wait()

    def disconnect(self):
        if self.cast:
            self.cast.disconnect()
            self.cast = None

    def play(self, url, mimetype):
        if self.cast is None:
            self.connect()
        self.stop()
        mc = self.cast.media_controller
        mc.play_media(url, mimetype, stream_type="BUFFERED")
        mc.block_until_active()
        #mc.enable_subtitle(0)

    def stop(self):
        if self.cast is not None and not self.cast.is_idle:
            self.cast.quit_app()
            time.sleep(1)
