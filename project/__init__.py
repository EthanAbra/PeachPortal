from gevent import monkey
monkey.patch_all()

from flask import Flask, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from flask_login import LoginManager, current_user
from flask_cors import CORS
import os
import urllib3
from . import database as db
import uuid
import polyfile
import random
import logging




from .xlsxMethods import xlsxRead
from bson.binary import Binary

from flask_socketio import SocketIO

from .settings import app

from engineio.payload import Payload


Payload.max_decode_packets = 500
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




socketio = SocketIO(engineio_logger=True)
login_manager = LoginManager()


def create_app(debug = False):
    with app.app_context():
        from . import auth, routes

        # Register Blueprints
        app.register_blueprint(routes.main_bp)
        app.register_blueprint(auth.auth_bp)
        app.debug = debug


        login_manager.login_view = '/login'
        login_manager.init_app(app)
        print('login manager inited')
        socketio.init_app(app)
        return app


