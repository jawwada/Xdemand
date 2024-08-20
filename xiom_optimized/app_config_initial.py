import dash
import dash_auth
import dash_bootstrap_components as dbc
from flask import Flask

from xiom_optimized.utils.config_constants import VALID_USERNAME_PASSWORD_PAIRS

server = Flask(__name__)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.ZEPHYR],
    server=server)
app.title = 'X-Demand'
app.config['suppress_callback_exceptions'] = False
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)
