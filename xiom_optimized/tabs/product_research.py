from dash import dcc, html
import dash_bootstrap_components as dbc
from xiom_optimized.dash_callbacks.product_research_callbacks import *

layout = html.Div([
    html.H1("Product Research"),
    html.Hr(),
    html.Div([
        html.H3("Review Search"),
        dbc.Input(id="search-input", type="text", placeholder="Enter your search query"),
        dbc.Button("Search", id="search-button", color="primary", className="mr-2"),
        html.Div(id="search-results", className="mt-3")
    ], className='row')
])