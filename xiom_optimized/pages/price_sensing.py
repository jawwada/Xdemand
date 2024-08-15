from xiom_optimized.pages.price_sensing_callbacks import *

from xiom_optimized.utils.utils import get_unique_values

unique_skus = get_unique_values('sku')
default_sku = unique_skus[0] if unique_skus else None

content = html.Div([
    # Forecasting Graphs
    # html.H4('Analyze Customer Price Interaction', style={'color': 'white'}),
    html.Div([
        dcc.Tabs(id="ps-tabs",
                 value='ps-tab-1', children=[
                dcc.Tab(label='Graph', value='ps-tab-1'),
                dcc.Tab(label='Data', value='ps-tab-2'),
            ]),
    ], className="row"),
    html.Div(id='ps-tabs-content', className="row"),
    html.Hr(),
    html.Div([
        html.Div(id='sku-price-sensing-container')
    ], className="row")
], className="col")
layout = html.Div([
    html.Div([content], style={'margin-left': '0px'}),
], className="col-md-12")
