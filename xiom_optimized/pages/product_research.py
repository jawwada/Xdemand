from dash import dcc
from dash import html

from xiom_optimized.utils.utils import get_unique_values

unique_skus = get_unique_values('sku')
default_sku = unique_skus[0] if unique_skus else None

layout = html.Div([
    html.H1("Product Research"),

    # SKU Dropdown
    dcc.Dropdown(
        id='sku-dropdown',
        options=[{'label': i, 'value': i} for i in unique_skus],
        value=default_sku,
        placeholder='Select SKU'
    ),

    # Seasonality Mode Radio Buttons
    dcc.RadioItems(
        id='seasonality-mode-radio',
        options=[
            {'label': 'Multiplicative', 'value': 'multiplicative'},
            {'label': 'Additive', 'value': 'additive'}
        ],
        value='multiplicative',
        labelStyle={'display': 'inline-block'}
    ),

    # Demand Forecasting Graph
    html.Div(id='demand-forecasting-graph'),

    # Price Elasticity Graph
    html.Div(id='price-elasticity-graph'),

    # Stock Forecasting Graph
    html.Div(id='stock-forecasting-graph'),

    # Price Recommender Graph
    html.Div(id='price-recommender-graph'),

    # Ask AI Section
    html.Div([
        dcc.Textarea(
            id='ai-question',
            placeholder='Ask AI about this product...',
            style={'width': '100%', 'height': 100}
        ),
        html.Button('Submit', id='ai-submit-button', className='btn btn-primary'),
        html.Div(id='ai-response')
    ], className="mt-4")
])
