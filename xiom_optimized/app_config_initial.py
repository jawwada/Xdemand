import os

import dash
import dash_auth
import dash_bootstrap_components as dbc
from flask import Flask

from xiom_optimized.utils.config_constants import VALID_USERNAME_PASSWORD_PAIRS

# check if the environment variable is set
if os.getenv('OPENAI_API_KEY') is None:
    print("Setting the environment variable, because it is not set")
    # set the environment variable
    os.environ["OPENAI_API_KEY"] = "sk-proj-qJUXLz3esJY0E5SEpTQcT3BlbkFJA94UzfVp9l7AF2zmnhkL"
server = Flask(__name__)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.ZEPHYR],
    external_scripts=[
        {'src': 'https://cdn.jsdelivr.net/npm/dom-to-image@2.6.0/dist/dom-to-image.min.js'}
    ],
    server=server)
app.title = 'X-Demand'
app.config['suppress_callback_exceptions'] = False
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)
