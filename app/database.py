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

import sqlite3
import string
import random
import os
import time
import datetime
from passlib.hash import sha512_crypt


class Database:
    def __init__(self, filename):
        self._conn = sqlite3.connect(filename)
        c = self._conn.cursor()
        c.execute("PRAGMA foreign_keys = ON")

    def init(self):
        c = self._conn.cursor()

        c.execute(
            "CREATE TABLE IF NOT EXISTS user ("
            "id         INTEGER PRIMARY KEY,"
            "name       TEXT UNIQUE NOT NULL,"
            "password   TEXT NOT NULL)"
        )

        c.execute(
            "CREATE TABLE IF NOT EXISTS link ("
            "identifier TEXT UNQIUE NOT NULL,"
            "user_id    INTEGER REFERENCES user(id) ON DELETE CASCADE ON UPDATE RESTRICT,"
            "path       TEXT NOT NULL,"
            "timestamp  INTEGER NOT NULL)"
        )

        c.execute("CREATE INDEX IF NOT EXISTS link_index ON link(user_id, path)")

        c.execute(
            "CREATE TABLE IF NOT EXISTS directory ("
            "id         INTEGER PRIMARY KEY,"
            "path       TEXT UNIQUE NOT NULL,"
            "name       TEXT NOT NULL)"
        )

        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS directory_name_index ON directory(name)")

        c.execute(
            "CREATE TABLE IF NOT EXISTS access ("
            "user_id        INTEGER REFERENCES user(id) ON DELETE CASCADE ON UPDATE RESTRICT,"
            "directory_id   INTEGER REFERENCES directory(id) ON DELETE CASCADE ON UPDATE RESTRICT,"
            "level          INTEGER DEFAULT 0)"
        )

        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS access_user_index ON access(user_id, directory_id)"
        )

        self._conn.commit()

    def close(self):
        self._conn.close()

    def addUser(self, name, password):
        h = sha512_crypt.hash(password)
        c = self._conn.cursor()
        c.execute("SELECT id FROM user WHERE name = ? LIMIT 1", (name,))
        r = c.fetchone()
        if r is None:
            c.execute("INSERT INTO user (name, password) VALUES (?, ?)", (name, h))
        else:
            c.execute("UPDATE user SET password = ? WHERE name = ?", (h, name))
        self._conn.commit()

    def authUser(self, name, password):
        c = self._conn.cursor()
        c.execute("SELECT password FROM user WHERE name = ? LIMIT 1", (name,))
        r = c.fetchone()
        if r is None:
            return False
        return sha512_crypt.verify(password, r[0])

    def delUser(self, name):
        c = self._conn.cursor()
        c.execute("DELETE FROM user WHERE name = ?", (name,))
        self._conn.commit()

    def addDirectory(self, path, name=""):
        path = path.rstrip(os.sep)
        if not os.path.isdir(path):
            raise Exception("Path is not a directory")
        if len(name) == 0:
            name = os.path.basename(path)
        c = self._conn.cursor()
        c.execute("INSERT OR IGNORE INTO directory (path, name) VALUES (?, ?)", (path, name))
        self._conn.commit()

    def delDirectory(self, path):
        path = path.rstrip(os.sep)
        c = self._conn.cursor()
        c.execute("DELETE FROM directory WHERE path = ?", (path,))
        self._conn.commit()

    def setDirectoryAccess(self, path, username, level):
        path = path.rstrip(os.sep)
        c = self._conn.cursor()
        c.execute("SELECT id FROM user WHERE name = ? LIMIT 1", (username,))
        r = c.fetchone()
        if r is None:
            raise Exception("User does not exist")
        user_id = r[0]
        c.execute("SELECT id FROM directory WHERE path = ? LIMIT 1", (path,))
        r = c.fetchone()
        if r is None:
            raise Exception("Directory does not exist")
        directory_id = r[0]
        c.execute(
            "INSERT OR REPLACE INTO access (user_id, directory_id, level) VALUES (?, ?, ?)",
            (user_id, directory_id, level),
        )
        self._conn.commit()

    def addDirectoryForUser(self, path, username, level=2):
        self.addDirectory(path)
        self.setDirectoryAccess(path, username, level)

    def delDirectoryForUser(self, path, username):
        self.setDirectoryAccess(path, username, 0)

    def getDirectoriesForUser(self, username):
        c = self._conn.cursor()
        c.execute("SELECT id FROM user WHERE name = ? LIMIT 1", (username,))
        r = c.fetchone()
        if r is None:
            raise Exception("User does not exist")
        user_id = r[0]
        c.execute(
            "SELECT d.path, d.name, a.level FROM directory AS d INNER JOIN access AS a ON a.directory_id = d.id AND a.user_id = ? LIMIT 1",
            (user_id,),
        )
        rows = c.fetchall()
        d = {}
        for r in rows:
            if r[2] > 0:
                d[r[1]] = (r[0], r[2])
        return d

    def resolveDirectory(self, username, path):
        c = self._conn.cursor()
        c.execute("SELECT id FROM user WHERE name = ? LIMIT 1", (username,))
        r = c.fetchone()
        if r is None:
            raise Exception("User does not exist")
        user_id = r[0]
        s = path.rstrip("/").split("/")
        if len(s) == 0:
            return None
        directory = s[0]
        c.execute(
            "SELECT d.path, a.level FROM directory AS d INNER JOIN access AS a ON a.directory_id = d.id AND a.user_id = ? WHERE d.name = ? LIMIT 1",
            (user_id, directory),
        )
        r = c.fetchone()
        if r is None or r[1] <= 0:
            return None
        s[0] = r[0]
        resolvedPath = os.path.join(*s)
        level = r[1]
        return resolvedPath, level

    def createLink(self, username, path):
        timestamp = int(time.time())
        c = self._conn.cursor()
        c.execute("SELECT id FROM user WHERE name = ? LIMIT 1", (username,))
        r = c.fetchone()
        if r is None:
            raise Exception("User does not exist")
        user_id = r[0]
        while True:
            length = 8
            letters = string.ascii_lowercase + string.digits
            identifier = "".join(random.choice(letters) for i in range(length))
            c.execute("SELECT 1 FROM link WHERE identifier = ? LIMIT 1", (identifier,))
            if not c.fetchone():
                break
        c.execute(
            "INSERT INTO link (identifier, user_id, path, timestamp) VALUES (?, ?, ?, ?)",
            (identifier, user_id, path, timestamp),
        )
        self._conn.commit()
        return identifier

    def resolveLink(self, identifier):
        c = self._conn.cursor()
        c.execute(
            "SELECT u.name, l.path, l.timestamp FROM link AS l LEFT JOIN user AS u ON u.id = l.user_id WHERE identifier = ? LIMIT 1",
            (identifier,),
        )
        r = c.fetchone()
        if r is None:
            return None
        link_time = datetime.datetime.fromtimestamp(r[2])
        current_time = datetime.datetime.now()
        seconds = (current_time - link_time).total_seconds()
        if seconds > 7 * 24 * 60 * 60:  # 7 days
            return None  # expired
        return r[0], r[1]
