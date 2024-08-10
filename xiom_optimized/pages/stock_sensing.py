from dash import dcc
from dash import html
from xiom_optimized.utils import get_unique_values
from xiom_optimized.pages.stock_sensing_callbacks import *
#from xiom_optimized.pages.data_chooser import sku_warehouse_selector

content = html.Div([
    # Forecasting Graphs
    html.Div([
        dcc.Tabs(id="stockout-tabs", value='so-tab-1', children=[
        dcc.Tab(label='Graph', value='so-tab-1'),
        dcc.Tab(label='Data', value='so-tab-2'),
    ]),
    ], className="row"),

    html.Div(id='tabs-content-stockout'),
    html.Hr(),
    #sku_warehouse_selector,
    html.Hr(),
    html.Div([
        dcc.Tabs(id="sss-tabs", value='pr-tab-1', children=[
            dcc.Tab(label='Graph', value='pr-tab-1'),
            dcc.Tab(label='Data', value='pr-tab-2'),
        ]),], className="row"),
        html.Hr(),
        html.Div(id='tabs-content-sss'),
], className="col-md-12")

layout = content