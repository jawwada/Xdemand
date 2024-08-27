from dash import dcc, html
import dash_bootstrap_components as dbc
from xiom_optimized.dash_callbacks.product_research_callbacks import *

layout = html.Div([
    # New section for SKU and Warehouse graphs
    html.Div(className='row', children=[
        html.Div(className='col', children=[
            html.Div(id='weekly-sales-graph', className='mb-3'),  # Top left graph
            # The graphs for promotional rebates and OOS days will be rendered here
        ]),
        html.Div(className='col', children=[
            html.Div(id='price-adjustment-graph'),  # Right top graph
            dcc.Slider(id='price-slider', min=0, max=100, step=0.01, value=50,
                       marks={i: str(i) for i in range(0, 101, 10)}),
            dcc.Graph(id='trend-seasonality-graph')  # Below the slider
        ])
    ]),
    html.Hr(),
    html.Div([
        html.H3("Review Search"),
        dbc.Input(id="search-input", type="text", placeholder="Enter your search query"),
        dbc.Button("Search", id="search-button", color="primary", className="mr-2"),
        html.Div(id="search-results", className="mt-3")
    ], className='row'),

])