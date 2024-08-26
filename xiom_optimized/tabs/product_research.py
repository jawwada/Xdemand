from dash import dcc, html
import dash_bootstrap_components as dbc
from xiom_optimized.utils.utils import get_unique_values

unique_skus = get_unique_values('sku')
default_sku = unique_skus[0] if unique_skus else None

unique_warehouses = get_unique_values('warehouse_code')

layout = html.Div([
    html.H1("Product Research"),
    html.Div([
        html.Div([
            html.H3("Product Selector"),
            dcc.Dropdown(id='sku-dropdown', options=[{'label': i, 'value': i} for i in unique_skus],
                         placeholder='Select SKU', value=default_sku),
        ], className='col-md-6'),
        html.Div([
            html.H3("Warehouse Selector"),
            dcc.Dropdown(id='warehouse-dropdown', options=[{'label': i, 'value': i} for i in unique_warehouses],
                         placeholder='Select Warehouse'),
        ], className='col-md-6'),
    ], className='row'),
    html.Hr(),
    html.Div([
        html.H3("Review Search"),
        dbc.Input(id="search-input", type="text", placeholder="Enter your search query"),
        dbc.Button("Search", id="search-button", color="primary", className="mr-2"),
        html.Div(id="search-results", className="mt-3")
    ], className='row'),
    html.Hr(),
    html.Div([
        html.Div(id='tabs-content-product-research')
    ], className='row')
])