'''
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
'''

import logging
import sqlite3
from passlib.hash import sha512_crypt

class Database:
    def __init__(self, filename):
        self._conn = sqlite3.connect(filename)
        c = self._conn.cursor()
        c.execute("PRAGMA foreign_keys = ON");

    def init(self):
        c = self._conn.cursor()

        c.execute("CREATE TABLE IF NOT EXISTS user ("
            "id         INTEGER PRIMARY KEY,"
            "name       TEXT UNIQUE NOT NULL,"
            "password     TEXT NOT NULL)")

#        c.execute("CREATE TABLE IF NOT EXISTS directory ("
#            "id         INTEGER PRIMARY KEY,"
#            "path       TEXT UNIQUE NOT NULL,"
#            "name       TEXT NOT NULL)")
#
#        c.execute("CREATE TABLE IF NOT EXISTS access ("
#            "user_id        INTEGER REFERENCES user(id) ON DELETE CASCADE ON UPDATE RESTRICT,"
#            "directory_id   INTEGER REFERENCES directory(id) ON DELETE CASCADE ON UPDATE RESTRICT,"
#            "level          INTEGER DEFAULT 0)")
#
#        c.execute("CREATE INDEX IF NOT EXISTS access_user_index ON access(user_id)")
#        c.execute("CREATE INDEX IF NOT EXISTS access_directory_index ON access(directory_id)")

        self._conn.commit()

    def close(self):
        self._conn.close()

    def addUser(self, name, password):
        h = sha512_crypt.hash(password)
        c = self._conn.cursor()
        c.execute("INSERT INTO user (name, password) VALUES (?, ?)", (name, h))
        self._conn.commit()

    def authUser(self, name, password):
        c = self._conn.cursor()
        c.execute("SELECT password FROM user WHERE name =? LIMIT 1", (name,))
        r = c.fetchone()
        if r is None:
            return False
        return sha512_crypt.verify(password, r[0])

    def delUser(self, name):
        c = self._conn.cursor()
        c.execute("DELETE FROM user WHERE name = ?", (name,))
        self._conn.commit()
