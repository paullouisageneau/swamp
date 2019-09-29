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

from gevent import monkey

monkey.patch_all()

import flask
import urllib
import urllib.parse
import os

from functools import reduce, wraps
from flask import request
from werkzeug.utils import secure_filename
from ipaddress import ip_address, ip_network

from .database import Database
from .streamer import Streamer
from .cast import Cast

app = flask.Flask(__name__, static_url_path="/static")
app.config.from_object("config")
app.secret_key = os.urandom(16)

filesDirectory = os.path.join(app.root_path, "files")
databaseFile = os.path.join(app.root_path, "database.db")

db = Database(databaseFile)
db.init()


def url_base(urlpath):
    return app.config["BASE_PATH"] + urlpath


def url_for(*args, **kwargs):
    return url_base(flask.url_for(*args, **kwargs))


def url_absolute(relative_url):
    return app.config["PREFERRED_URL_SCHEME"] + "://" + request.host + relative_url


def url_quote(path):
    return urllib.parse.quote(path)


def allowed_file(name):
    ext = os.path.splitext(name)[1][1:].lower()
    return ext not in ["php", "htm", "html", "js"]


def get_directory_path(username, urlpath):
    urlpath = urlpath.split("?", 2)[0]
    r = db.resolveDirectory(username, urlpath)
    if r:
        path, level = r
        if level >= 1:
            return path, (level >= 2)
    userDirectory = os.path.join(filesDirectory, username)
    if not os.path.isdir(userDirectory):
        os.makedirs(userDirectory)
    s = [userDirectory] + urlpath.rstrip("/").split("/")
    return os.path.join(*s), True


class FileInfo:
    def __init__(self, path, urlpath, writable=False):
        self.path = path
        self.name = os.path.basename(path)
        self.isdir = os.path.isdir(path)
        self.ext = os.path.splitext(path)[1][1:]
        self.isvideo = self.ext in ["avi", "mkv", "mp4"]
        self.urlpath = urlpath
        self.writable = writable


@app.context_processor
def inject():
    return dict(url_for=url_for, url_quote=url_quote)


def auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        mimetypes = ["application/octet-stream", "text/html"]
        if "username" in flask.session:
            flask.g.username = flask.session["username"]
            return f(*args, **kwargs)
        elif request.authorization:
            auth = request.authorization
            if db.authUser(auth.username, auth.password):
                flask.g.username = auth.username
                return f(*args, **kwargs)
        elif request.accept_mimetypes.best_match(mimetypes) == "text/html":
            return flask.redirect(url_for("login", url=url_base(request.full_path)), code=302)

        return flask.Response(
            "Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Swamp"'}
        )

    return decorated


def local(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        addr = ip_address(
            request.access_route[0] if len(request.access_route) > 0 else request.remote_addr
        )
        if addr.is_loopback or addr.is_private or addr.is_link_local:
            return f(*args, **kwargs)
        for net in app.config.get("CAST_ALLOWED_NETWORKS", []):
            if addr in ip_network(net):
                return f(*args, **kwargs)
        flask.abort(403)

    return decorated


@app.route("/", methods=["GET"])
def home():
    if "username" in flask.session:
        return flask.redirect(url_for("file"), code=307)  # same method
    else:
        return flask.redirect(url_for("login"), code=307)  # same method


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        if db.authUser(data["username"], data["password"]):
            flask.session["username"] = data["username"]
            if "url" in request.args:
                return flask.redirect(request.args["url"], code=302)
            else:
                return flask.redirect(url_for("home"), code=302)
        else:
            return flask.redirect(url_for("login"), code=302)
    else:  # GET
        return flask.render_template("login.html")


@app.route("/file/", methods=["GET", "POST"])
@app.route("/file/<path:urlpath>", methods=["GET", "POST"])
@auth
def file(urlpath=""):
    path, writable = get_directory_path(flask.g.username, urlpath)
    if request.method == "POST":
        if not writable:
            flask.abort(403)
        if not os.path.isdir(path):
            if not os.path.isfile(path):
                flask.abort(404)
            else:
                flask.abort(400)
        if len(urlpath) > 0 and urlpath[-1] != "/":
            urlpath += "/"
        data = request.form
        files = request.files
        if "file" in files and files["file"].filename != "":
            f = request.files["file"]
            if not allowed_file(f.filename):
                flask.abort(403)
            filename = secure_filename(f.filename)
            f.save(os.path.join(path, filename))
        elif "operation" in data and "argument" in data:
            operation = data["operation"]
            argument = data["argument"]
            suburlpath = urlpath + argument
            subpath, subwritable = get_directory_path(flask.g.username, suburlpath)
            if not subwritable:
                flask.abort(403)
            if operation == "delete":
                if os.path.isdir(subpath):
                    os.rmdir(subpath)
                else:
                    os.remove(subpath)
            elif operation == "create":
                os.makedirs(subpath)
            else:
                flask.abort(400)
        else:
            flask.abort(400)
        return flask.redirect(url_base(request.path), code=302)
    else:  # GET
        if os.path.isdir(path):
            if request.path[-1] != "/":
                query = request.query_string.decode()
                return flask.redirect(
                    url_base(request.path + "/") + ("?" + query if query else ""), code=302
                )
            if "link" in request.args:
                if len(urlpath) == 0:
                    flask.abort(400)
                identifier = db.createLink(flask.g.username, urlpath)
                return flask.redirect(
                    url_for("link", identifier=identifier) + "?display", code=302
                )
            files = list(
                map(
                    lambda f: FileInfo(os.path.join(path, f), urlpath + f, writable),
                    os.listdir(path),
                )
            )
            files = list(
                filter(lambda f: f.name[0] != "." and (f.isdir or allowed_file(f.name)), files)
            )
            if len(urlpath) == 0:
                d = db.getDirectoriesForUser(flask.g.username)
                directories = []
                for name in d:
                    path, level = d[name]
                    if level >= 1:
                        directories.append(FileInfo(path, name, level >= 2))
                files += directories
            files.sort(key=lambda f: "0" + f.name.lower() if f.isdir else "1" + f.name.lower())
            return flask.render_template(
                "directory.html", path="/" + urlpath, files=files, writable=writable
            )
        elif os.path.isfile(path):
            mimetypes = ["application/octet-stream", "text/html"]
            if request.accept_mimetypes.best_match(mimetypes) != "text/html":
                return flask.make_response(flask.send_file(path))
            elif "play" in request.args:
                identifier = db.createLink(flask.g.username, urlpath)
                seconds = 0
                if "start" in request.args:
                    a = map(lambda s: int(s), request.args["start"].split(":", 3))
                    seconds = reduce(lambda s, n: s * 60 + n, a)
                return flask.render_template(
                    "player.html",
                    title=os.path.basename(path),
                    downloadLocation=url_base(request.path) + "?download",
                    videoLocation=url_for("stream", identifier=identifier),
                    castLocation=url_for("cast", identifier=identifier),
                    videoTime=seconds,
                )
            elif "link" in request.args:
                identifier = db.createLink(flask.g.username, urlpath)
                return flask.redirect(
                    url_for("link", identifier=identifier) + "?display", code=302
                )
            else:
                response = flask.make_response(flask.send_file(path))
                if "download" in request.args:
                    response.headers["Content-Type"] = "application/octet-stream"
                    response.headers["Content-Disposition"] = (
                        'attachment; filename="' + os.path.basename(path) + '"'
                    )
                return response
        else:
            flask.abort(404)


def resolve(identifier, subpath=None):
    r = db.resolveLink(identifier)
    if not r:
        flask.abort(404)
    username, urlpath = r
    if subpath:
        urlpath += "/" + subpath
    path, _ = get_directory_path(username, urlpath)
    return username, urlpath, path


@app.route("/link/<identifier>", methods=["GET"], defaults={"subpath": None})
@app.route("/link/<identifier>/", methods=["GET"], defaults={"subpath": None})
@app.route("/link/<identifier>/<path:subpath>", methods=["GET"])
def link(identifier, subpath):
    username, urlpath, path = resolve(identifier, subpath)
    if "display" in request.args:
        link = url_absolute(url_for("link", identifier=identifier))
        return flask.render_template("link.html", link=link, filename=os.path.basename(path))
    if os.path.isdir(path):
        if request.path[-1] != "/":
            query = request.query_string.decode()
            return flask.redirect(
                url_base(request.path + "/") + ("?" + query if query else ""), code=302
            )
        files = list(
            map(lambda f: FileInfo(os.path.join(path, f), urlpath + f, False), os.listdir(path))
        )
        files = list(
            filter(lambda f: f.name[0] != "." and (f.isdir or allowed_file(f.name)), files)
        )
        files.sort(key=lambda f: "0" + f.name.lower() if f.isdir else "1" + f.name.lower())
        return flask.render_template("safe_directory.html", files=files)
    return flask.send_file(path, as_attachment=True)


@app.route("/stream/<identifier>/", methods=["GET"], defaults={"subpath": None})
@app.route("/stream/<identifier>/<path:subpath>", methods=["GET"])
def stream(identifier, subpath):
    default_range = "bytes=0-"
    if request.headers.get("Range", default_range) != default_range:
        flask.abort(416)  # Range not satisfiable
    username, urlpath, path = resolve(identifier, subpath)
    stream_format = request.args.get('format', 'webm')
    s = Streamer(path, stream_format)
    if "info" in request.args:
        return flask.jsonify(s.get_description())
    is_hd = bool(request.args.get('hd', False))
    start = request.args["start"] if "start" in request.args else None
    f = s.get_stream(is_hd, start)
    return flask.Response(f, direct_passthrough=True, mimetype=s.mimetype)


@app.route("/cast/<identifier>/", methods=["GET", "POST"], defaults={"subpath": None})
@app.route("/cast/<identifier>/<path:subpath>", methods=["GET", "POST"])
@local
def cast(identifier, subpath):
    cast = Cast()
    if cast is None:
        flask.abort(503)  # Service unavailable
    username, urlpath, path = resolve(identifier, subpath)
    if "list" in request.args:
        cast = Cast()
        devices = cast.list() if cast is not None else []
        return flask.jsonify({"devices": devices})
    cast.connect(request.args.get("host", None))
    if request.method == "POST":
        query = "?format=matroska&hd=1"
        if "start" in request.args:
            query += "&start={}".format(request.args["start"])
        if "audio" in request.args:
            query += "&audio={}".format(request.args["audio"])
        cast_url = url_absolute(url_for("stream", identifier=identifier, subpath=subpath) + query)
        cast.play(cast_url, "video/x-matroska")
    return flask.jsonify({})


# Import main to expose it outside
from .__main__ import main
