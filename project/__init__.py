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

Payload.max_decode_packets = 500
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




socketio = SocketIO(engineio_logger=True, logger = True)
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
        socketio.init_app(app)
        bkapp = Application(FunctionHandler(my_gui))

        # This is so that if this app is run using something like "gunicorn -w 4" then
        # each process will listen on its own port
        sockets, port = bind_sockets("0.0.0.0", 0)
        app._bokehport = port


        def bk_worker():

            asyncio.set_event_loop(asyncio.new_event_loop())

            bokeh_tornado = BokehTornado({'/bkapp': bkapp}, extra_websocket_origins=["localhost", "peachportal.azurewebsites.net"])
            bokeh_http = HTTPServer(bokeh_tornado)
            bokeh_http.add_sockets(sockets)

            server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
            server.start()
            server.io_loop.start()

        from threading import Thread
        Thread(target=bk_worker).start()
        return app


