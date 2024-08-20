from dash import dcc
from dash import html

from xiom_optimized.utils.utils import get_unique_values

unique_skus = get_unique_values('sku')
default_sku = unique_skus[0] if unique_skus else None

layout = html.Div([
    html.H1("Product Research"),
    html.Div([
        html.Div([
            html.H3("Product Selector"),
            dcc.Dropdown(id='sku-dropdown', options=[{'label': i, 'value': i} for i in unique_skus],
                         placeholder='Select SKU', value=default_sku),
        ], className='col'),
    ], className='row'),
    html.Hr(),
    html.Div([
        html.Div(id='tabs-content-product-research')
    ], className='row')
])