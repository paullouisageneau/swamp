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
from flask import request, Response, url_for
from werkzeug.utils import secure_filename

from . import database
from . import streamer

app = flask.Flask(__name__)
app.config.from_object(__name__)
app.secret_key = os.urandom(16)

filesDirectory = os.path.join(app.root_path, 'files')
databaseFile = os.path.join(app.root_path, 'database.db')

db = database.Database(databaseFile)
db.init()

def getDirectoryPath(username, urlpath):
    userDirectory = os.path.join(filesDirectory, username)
    if not os.path.isdir(userDirectory):
        os.makedirs(userDirectory)
    return os.path.join(userDirectory, urlpath.split('?', 2)[0])

class FileInfo:
    def __init__(self, path, urlpath):
        self.path = path
        self.name = os.path.basename(path)
        self.isdir = os.path.isdir(path)
        self.ext = os.path.splitext(path)[1][1:]
        self.isvideo = self.ext in ['avi', 'mkv', 'mp4']
        self.urlpath = urlpath

def auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' in flask.session:
            flask.g.username = flask.session['username']
            return f(*args, **kwargs)
        else:
            return flask.redirect(url_for('login', url=request.full_path), code=302)
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
    path = getDirectoryPath(username, urlpath)
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
    path = getDirectoryPath(flask.g.username, urlpath)
    if request.method == 'POST':
        data = request.form
        files = request.files
        if not os.path.isdir(path):
            if not os.path.isfile(path):
                flask.abort(404)
            else:
                flask.abort(400)
        if 'file' in files and files['file'].filename != '':
            f = request.files['file']
            filename = secure_filename(f.filename)
            f.save(os.path.join(path, filename))
        elif 'action' in data:
            action = data['action']
            name = data.get('name', '')
            if action == 'delete':
                pass
        else:
            flask.abort(400);
        return flask.redirect(request.path, code=302)
    else: # GET
        if os.path.isdir(path):
            if path[-1] != '/':
                return flask.redirect(request.path+"/"+request.query_string, code=302)
            files = map(lambda f: FileInfo(os.path.join(path, f), urlpath+f), os.listdir(path))
            return flask.render_template("directory.html", path=urlpath, files=files)
        elif os.path.isfile(path):
            if 'play' in request.args:
                seconds = 0;
                if 'start' in request.args:
                    a = map(lambda s: int(s), request.args['start'].split(':', 3))
                    seconds = reduce(lambda s, n: s*60 + n, a)
                return flask.render_template("player.html",
                    downloadLocation=request.path,
                    videoLocation="/stream/"+urlpath,
                    videoTime=seconds)
            elif 'link' in request.args:
                identifier = db.createLink(flask.g.username, urlpath)
                return flask.redirect(url_for('link', identifier=identifier), code=302)
            else:
                return flask.send_file(path)
        else:
            flask.abort(404)

@app.route("/stream/<path:urlpath>", methods=['GET'])
@auth
def stream(urlpath):
    path = getDirectoryPath(flask.g.username, urlpath)
    s = streamer.Streamer(path)
    if 'playinfo' in request.args:
        return flask.jsonify(s.getDescription())
    if 'castinfo' in request.args:
        flask.abort(404)
    f = s.getWebmStream(False, request.args['start'] if 'start' in request.args else '')
    return Response(f, direct_passthrough=True, mimetype='video/webm')
