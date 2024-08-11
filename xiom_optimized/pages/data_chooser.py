import pandas as pd
from dash import dcc, html
from datetime import datetime, timedelta
from xiom_optimized.pages.data_chooser_callbacks import *
from xiom_optimized.utils import get_unique_values
unique_skus = get_unique_values('sku')
default_sku = unique_skus[0] if unique_skus else None

start_date = (datetime.now() - timedelta(days=365)).date()
end_date = datetime.now().date()

def format_sql_values(values):
    if len(values) == 1:
        return f"('{values[0]}')"
    else:
        return str(tuple(values))


dim_selector = html.Div(
    [
        # Sales Data Radio Buttons
        html.Div(
            [
                dcc.RadioItems(
                    id='quantity-sales-radio',
                    options=[
                        {'label': 'Quantity', 'value': 'quantity'},
                        {'label': 'Sales', 'value': 'revenue'}
                    ],
                    value='quantity',
                    labelStyle={'display': 'block'}
                )
            ],
            style={'columnCount': 2, 'width': '200px'}
        )
    ],id='dim-selector'
)

ph_selector=html.Div([
    html.Hr(),
    dcc.Dropdown(id='channel-dropdown', options=[{'label': 'ALL', 'value': ''}], placeholder='Select Channel'),
    dcc.Dropdown(id='warehouse-code-dropdown', options=[{'label': 'ALL', 'value': ''}], placeholder='Select Warehouse'),
    dcc.Dropdown(id='region-dropdown', options=[{'label': 'ALL', 'value': ''}], placeholder='Select Region'),
    dcc.Dropdown(id='category-dropdown', options=[{'label': 'ALL', 'value': ''}], placeholder='Select Category'),
    dcc.Dropdown(id='subcategory-dropdown', options=[{'label': 'ALL', 'value': ''}], placeholder='Select Subcategory',
                 style={'display': 'none'}
                 ),
    dcc.Dropdown(id='group1-dropdown', options=[{'label': 'ALL', 'value': ''}], placeholder='Select Group 1',
                 style = {'display': 'none'}
                 ),
    dcc.Dropdown(id='group2-dropdown', options=[{'label': 'ALL', 'value': '' }], placeholder='Select Group 2',
         style = {'display': 'none'}
                 ),
    dcc.Dropdown(id='sku-dropdown', options=[{'label': i, 'value': i} for i in unique_skus], placeholder='Select SKU'),
    ])

time_range_selector = html.Div([
    html.H6('Time Range',className="mt-4"),
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date_placeholder_text="Start Period",
        end_date_placeholder_text="End Period",
        min_date_allowed=start_date,
        max_date_allowed=end_date,
    ),
], className="mt-4")
time_selector=html.Div([
    html.H6('Detail level', className="mt-4"),
    # Time Period Slider
    dcc.Slider(
        id='sample-rate-slider',
        value=1,
        step=1,
        marks={
            0: {'label': 'Daily'},
            1: {'label': 'Weekly'},
            2: {'label': 'Monthly'}
        })
],id='time-selector')


data_chooser = html.Div([
        html.Div([
            dcc.Store(id='filter-data', data=ph_data.to_json(date_format='iso', orient='split'),storage_type='session'),
            # Sales Data Radio Buttonns
        html.H5('   Selection Criteria'),
        dim_selector,
        ph_selector,
        #time_range_selector,
        time_selector,
        #html.Button('Submit', id='submit-button', className='btn btn-primary mt-4'),
    ])
], id='data-chooser')
 #   , style={'display': 'none'})