import os
from flask import Flask


TEMPLATE_DIR = '../templates'
STATIC_DIR = '../static'

if 'secret_key' not in os.environ:
    from dotenv import load_dotenv
    load_dotenv()
    secret_key = os.environ.get('secret_key')
else:
    secret_key = os.environ['secret_key']



app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

app.secret_key = secret_key
app.config['SECRET_KEY'] = app.secret_key

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024* 20