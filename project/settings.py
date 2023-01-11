import os
from flask import Flask
from dotenv import load_dotenv

TEMPLATE_DIR = '.././templates'
STATIC_DIR = '.././static'




load_dotenv()
if 'database_url' not in os.environ:
    CONNECTION_STRING = os.environ.get('database_url')
else:
    CONNECTION_STRING = os.environ['database_url']

if 'secret_key' not in os.environ:
    secret_key = os.environ.get('secret_key')
else:
    secret_key = os.environ['secret_key']



app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

app.secret_key = secret_key
app.config['SECRET_KEY'] = app.secret_key

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024* 20

app.config['MONGO_URI'] = CONNECTION_STRING



