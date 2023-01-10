from gevent import monkey
monkey.patch_all()
from flask_login import LoginManager
import os
import urllib3
import random
from flask_socketio import SocketIO
from .settings import app
from engineio.payload import Payload
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from .splitpieces import my_gui
import asyncio
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask_mail import Mail
import os
from flask_jwt_extended import JWTManager
import random

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
        if os.environ.get('ENV') == 'PRODUCTION':
            while True:
                try:
                    tryport = random.randint(5555,6000)
                    sockets, port = bind_sockets("0.0.0.0", tryport)
                    break
                except:
                    pass
        else:
             while True:
                try:
                    tryport = random.randint(5555,6000)
                    sockets, port = bind_sockets("localhost", tryport)
                    break
                except:
                    pass
        app._bokehport = port
        print("Bokeh port: ")
        print(app._bokehport)

        def bk_worker():

            asyncio.set_event_loop(asyncio.new_event_loop())
            #TODO: this makes me uncomfortable, but I don't know how to do it better
            bokeh_tornado = BokehTornado({'/bkapp': bkapp}, extra_websocket_origins=["localhost", "20.127.116.12", "www.peachrow.net"])
            if os.environ.get('ENV') == 'PRODUCTION':
                bokeh_http = HTTPServer(bokeh_tornado ,  ssl_options={"certfile": './.domain.crt', "keyfile":'./.domain.rsa'})
            else: 
                bokeh_http = HTTPServer(bokeh_tornado)
            bokeh_http.add_sockets(sockets)
            server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
            server.start()
            server.io_loop.start()

        if os.environ.get('ENV') == 'PRODUCTION':
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


