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
import sys
import os
import getpass

import gevent.wsgi

from . import app, db
from . import database

port = 8085

def command(a):
	assert a
	obj = a.pop()
	if obj == 'user':
		if not len(a):
			print("Missing operation")
			return 2
		opr = a.pop()
		if opr == 'add':
			if not len(a):
				print("Missing user name")
				return 2
			username = a.pop()
			if len(a):
				password = a.pop()
			else:
				password = getpass.getpass()
			db.addUser(username, password)
		elif opr == 'del':
			if not len(a):
				print("Missing user name")
				return 2
			db.delUser(username)
		else:
			print("Unknown operation, expected 'add' or 'del'")
	elif obj == 'dir' or obj == 'directory':
		if not len(a):
			print("Missing operation")
			return 2
		opr = a.pop()
		if opr == 'add':
			if not len(a):
				print("Missing path")
				return 2
			path = a.pop()
			if len(a):
				username = a.pop()
				access = 2
				if len(a):
					access = a.pop()
				db.addDirectoryForUser(path, username, access)
			else:
				db.addDirectory(path)
		elif opr == 'del':
			if not len(a):
				print("Missing path")
				return 2
			path = a.pop()
			db.delDirectory(path)
		else:
			print("Unknown operation, expected 'add' or 'del'")
	else:
		print("Unknown argument, expected 'user' or 'dir'")
	return 0

def main():
	a = list(reversed(sys.argv));
	assert len(a)
	a.pop()
	if len(a) and not (len(a) == 1 and a[0] == 'run'):
		return command(a)
	else:
		try:
			print("Listening on http://127.0.0.1:{}/".format(port))
			http_server = gevent.wsgi.WSGIServer(("127.0.0.1", port), app)
			http_server.serve_forever()
		except KeyboardInterrupt:
			return 0

		return 1

if __name__ == "__main__":
	sys.exit(main())
