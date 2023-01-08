from gevent import monkey
monkey.patch_all()

from flask import Flask, g, current_app
from flask_login import LoginManager, current_user
import os
import urllib3
import uuid
import polyfile
import random
import logging
from .xlsxMethods import xlsxRead
from bson.binary import Binary
from flask_socketio import SocketIO
from .settings import app
import pymongo
from pymongo import MongoClient
from engineio.payload import Payload
import certifi
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from .splitpieces import my_gui
import asyncio
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask_mail import Mail, Message
import os
from flask_jwt_extended import JWTManager

Payload.max_decode_packets = 500
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




socketio = SocketIO(engineio_logger=True, logger = True)
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()

def create_app(debug = False):
    with app.app_context():
        from . import auth, routes

        # Register Blueprints
        app.register_blueprint(routes.main_bp)
        app.register_blueprint(auth.auth_bp)
        app.debug = debug

        login_manager.login_view = '/login'
        login_manager.init_app(app)
        socketio.init_app(app)
        bkapp = Application(FunctionHandler(my_gui))

        # This is so that if this app is run using something like "gunicorn -w 4" then
        # each process will listen on its own port
        sockets, port = bind_sockets("0.0.0.0", 5559)
        app._bokehport = port
        print("Bokeh port: ")
        print(app._bokehport)

        def bk_worker():

            asyncio.set_event_loop(asyncio.new_event_loop())
            #TODO: this makes me uncomfortable, but I don't know how to do it better
            bokeh_tornado = BokehTornado({'/bkapp': bkapp}, extra_websocket_origins=["localhost", "20.127.116.12", "www.peachrow.net"])
            bokeh_http = HTTPServer(bokeh_tornado,  ssl_options={"certfile": './.domain.crt', "keyfile":'./.domain.rsa'})
            bokeh_http.add_sockets(sockets)
            server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
            server.start()
            server.io_loop.start()

        # TODO: HIDE THESE BOIS
        app.config['MAIL_SERVER'] = os.environ.get('mail_server')
        app.config['MAIL_PORT'] = int(os.environ.get('mail_port'))
        app.config['MAIL_USE_SSL'] = os.getenv("mail_use_ssl", 'False').lower() in ('true', '1', 't')
        app.config['MAIL_USE_TLS'] = os.getenv("mail_use_tls", 'False').lower() in ('true', '1', 't')
        app.config['MAIL_USERNAME'] = os.environ.get('mail_username')
        app.config['MAIL_PASSWORD'] = os.environ.get('mail_password')
        mail.init_app(app)
        jwt.init_app(app)
        from threading import Thread
        Thread(target=bk_worker).start()
        return app


