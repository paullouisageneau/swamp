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
import urllib.parse
import flask

from functools import wraps
from flask import request, url_for
from werkzeug.utils import secure_filename

from . import database
from . import streamer

app = flask.Flask(__name__, static_url_path='/static')
app.config.from_object('config')
app.secret_key = os.urandom(16)

filesDirectory = os.path.join(app.root_path, 'files')
databaseFile = os.path.join(app.root_path, 'database.db')

db = database.Database(databaseFile)
db.init()

def url_for(*args, **kwargs):
        return app.config['BASE_PATH'] + flask.url_for(*args, **kwargs)

@app.context_processor
def inject():
        return dict(url_for=url_for)

def getDirectoryPath(username, urlpath):
	urlpath = urlpath.split('?', 2)[0]
	r = db.resolveDirectory(username, urlpath)
	if r:
		path, level = r
		if level >= 1:
			return path, (level >= 2)
	userDirectory = os.path.join(filesDirectory, username)
	if not os.path.isdir(userDirectory):
		os.makedirs(userDirectory)
	s = [userDirectory] + urlpath.rstrip('/').split('/')
	return os.path.join(*s), True

class FileInfo:
	def __init__(self, path, urlpath, writable = False):
		self.path = path
		self.name = os.path.basename(path)
		self.isdir = os.path.isdir(path)
		self.ext = os.path.splitext(path)[1][1:]
		self.isvideo = self.ext in ['avi', 'mkv', 'mp4']
		self.urlpath = urlpath
		self.writable = writable

def auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		if 'username' in flask.session:
			flask.g.username = flask.session['username']
			return f(*args, **kwargs)
		else:
			return flask.redirect(url_for('login', url=app.config['BASE_PATH']+request.full_path), code=302)
	return decorated

@app.route("/", methods=['GET'])
def home():
	if 'username' in flask.session:
		return flask.redirect(url_for('file'), code=307) # same method
	else:
		return flask.redirect(url_for('login'), code=307) # same method

@app.route("/link/<identifier>", methods=['GET'])
def link(identifier):
	r = db.resolveLink(identifier)
	if not r:
		flask.abort(404)
	username, urlpath = r
	path, writable = getDirectoryPath(username, urlpath)
	if not os.path.isfile(path):
		flask.abort(404)
	return flask.send_file(path)

@app.route("/login", methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		data = request.form
		if db.authUser(data['username'], data['password']):
			flask.session['username'] = data['username']
			if 'url' in request.args:
				return flask.redirect(request.args['url'], code=302)
			else:
				return flask.redirect(url_for('home'), code=302)
		else:
			return flask.redirect(url_for('login'), code=302)
	else: # GET
		return flask.render_template("login.html")

@app.route("/file/", methods=['GET', 'POST'])
@app.route("/file/<path:urlpath>", methods=['GET', 'POST'])
@auth
def file(urlpath = ""):
	path, writable = getDirectoryPath(flask.g.username, urlpath)
	if request.method == 'POST':
		if not writable:
			flask.abort(403)
		if not os.path.isdir(path):
			if not os.path.isfile(path):
				flask.abort(404)
			else:
				flask.abort(400)
		if len(urlpath) > 0 and urlpath[-1] != '/':
			urlpath+= '/'
		data = request.form
		files = request.files
		if 'file' in files and files['file'].filename != '':
			f = request.files['file']
			filename = secure_filename(f.filename)
			f.save(os.path.join(path, filename))
		elif 'operation' in data and 'argument' in data:
			operation = data['operation']
			argument = data['argument']
			suburlpath = urlpath+argument
			subpath, subwritable = getDirectoryPath(flask.g.username, suburlpath)
			if not subwritable:
				flask.abort(403)
			if operation == 'delete':
				if os.path.isdir(subpath):
					os.rmdir(subpath)
				else:
					os.remove(subpath)
			elif operation == 'create':
				os.makedirs(subpath)
			else:
				flask.abort(400)
		else:
			flask.abort(400);
		return flask.redirect(app.config['BASE_PATH']+request.path, code=302)
	else: # GET
		if os.path.isdir(path):
			if len(urlpath) > 0 and urlpath[-1] != '/':
				return flask.redirect(app.config['BASE_PATH']+request.path+"/"+request.query_string.decode(), code=302)
			files = list(map(lambda f: FileInfo(os.path.join(path, f), urlpath+f, writable), os.listdir(path)))
			if len(urlpath) == 0:
				d = db.getDirectoriesForUser(flask.g.username)
				directories = []
				for name in d:
					path, level = d[name]
					if level >= 1:
						directories.append(FileInfo(path, name, level >= 2))
				files+= directories
			files.sort(key=lambda fi: '0'+fi.name.lower() if fi.isdir else '1'+fi.name.lower())
			return flask.render_template("directory.html", path=urlpath, files=files, writable=writable)
		elif os.path.isfile(path):
			if 'play' in request.args:
				seconds = 0;
				if 'start' in request.args:
					a = map(lambda s: int(s), request.args['start'].split(':', 3))
					seconds = reduce(lambda s, n: s*60 + n, a)
				return flask.render_template("player.html",
					title = os.path.basename(path),
					downloadLocation = app.config['BASE_PATH']+request.path+'?download',
					videoLocation="/stream/"+urlpath,
					videoTime=seconds)
			elif 'link' in request.args:
				identifier = db.createLink(flask.g.username, urlpath)
				return flask.redirect(url_for('link', identifier=identifier), code=302)
			else:
				response = flask.make_response(flask.send_file(path));
				if 'download' in request.args:
					response.headers['Content-Type'] = 'application/octet-stream'
					response.headers['Content-Disposition'] = 'attachment; filename="'+os.path.basename(path)+'"';
				return response
		else:
			flask.abort(404)

@app.route("/stream/<path:urlpath>", methods=['GET'])
@auth
def stream(urlpath):
	path, writable = getDirectoryPath(flask.g.username, urlpath)
	s = streamer.Streamer(path)
	if 'playinfo' in request.args:
		return flask.jsonify(s.getDescription())
	if 'castinfo' in request.args:
		flask.abort(404)
	f = s.getWebmStream(False, request.args['start'] if 'start' in request.args else '')
	return flask.Response(f, direct_passthrough=True, mimetype='video/webm')
