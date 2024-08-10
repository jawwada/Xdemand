import pandas as pd
from xiom_optimized.app_config_initial import app
from xiom_optimized.caching import ph_data
from dash import Input, Output,State
from xiom_optimized.utils import filter_data




@app.callback(
Output('filter-data', 'data'),
Input('channel-dropdown', 'value'),
Input('warehouse-code-dropdown', 'value'),
Input('region-dropdown', 'value'),
Input('category-dropdown', 'value'),
Input('subcategory-dropdown', 'value'),
Input('group1-dropdown', 'value'),
Input('group2-dropdown', 'value'))
def update_filter_data(selected_channel, selected_warehouse,selected_region, selected_category, selected_subcategory, selected_group1, selected_group2):
    filtered_data = filter_data(pd.DataFrame(ph_data), selected_channel, selected_warehouse,
                                selected_region, selected_category, selected_subcategory,
                                selected_group1, selected_group2)
    return filtered_data


@app.callback(
    Output('channel-dropdown', 'options'),
    Input('filter-data', 'data'))
def update_channel_options(filtered_data):
    df= pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['channel'].unique()]
    return options


@app.callback(
    Output('warehouse-code-dropdown', 'options'),
    Input('filter-data', 'data'))

def update_warehouse_options(filtered_data):
    df= pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['warehouse_code'].unique()]
    return options

@app.callback(
    Output('region-dropdown', 'options',allow_duplicate=True),
    Input('filter-data', 'data'),
    prevent_initial_call=True
)
def update_region_options(filtered_data):
    df = pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['region'].unique()]
    return options

# Chained callback functions
@app.callback(
    Output('category-dropdown', 'options'),
    Input('filter-data', 'data'))
def update_category_options(filtered_data):
    df = pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['level_1'].unique()]
    return options


# Define a function to update the subcategory dropdown
@app.callback(
    Output('subcategory-dropdown', 'options'),
    Input('filter-data', 'data'))
def update_subcategory_options(filtered_data):
    df = pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['level_2'].unique()]
    return options



# Define a function to update the group 1 dropdown
@app.callback(
    Output('group1-dropdown', 'options'),
    Input('filter-data', 'data'))
def update_group1_options(filtered_data):
    df = pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['level_3'].unique()]
    return options



# Define a function to update the group 2 dropdown
@app.callback(
    Output('group2-dropdown', 'options'),
    Input('filter-data', 'data'))
def update_group2_options(filtered_data):
    df = pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['level_4'].unique()]
    return options

@app.callback(
    Output('sku-dropdown', 'options'),
    Input('filter-data', 'data'))
def update_sku_options(filtered_data):
    df = pd.read_json(filtered_data, orient='split')
    options = [{'label': i, 'value': i} for i in df['sku'].unique()]
    return options




