import urllib
from datetime import datetime
from datetime import timedelta
import dash_table
import pandas as pd
import plotly.express as px
from xiom_optimized.caching import cache, df_daily_sales_da, df_tree_map, df_sku_sum, df_agg_daily_3months, df_agg_weekly_year, df_agg_monthly_3years
from xiom_optimized.config_constants import *
from dash import html, dcc, Output, Input, State

from xiom_optimized.app_config_initial import app


@cache.memoize(timeout=TIMEOUT)
@app.callback(
    Output('da-tabs-content-analysis', 'children'),
    Input('quantity-sales-radio', 'value'),
    Input('sample-rate-slider', 'value'),
    Input('analysis-tabs', 'value'),
    State('filter-data', 'data'))
def update_demand_analysis_graph(quantity_sales_radio,time_window, graph_data_tab,filter_data=None):
    filtered_data = pd.DataFrame(filter_data)
    n_largest=10
    selected_sku = filtered_data['sku'].unique().tolist()
    n_largest=min(n_largest,len(selected_sku))

    df_dsa = df_daily_sales_da[df_daily_sales_da['sku'].isin(selected_sku)].copy(deep=True)
    num_skus = len(df_dsa['sku'].unique())
    # Create a dictionary to map the sample rate to the number of days to go back
    start_date = datetime.now() - timedelta(days=sample_rate_backdate_dict[sample_rate_dict[time_window]])
    # Filter the DataFrame based on the start date
    df_dsa = df_dsa[df_dsa['date'] >= start_date]

    # set 'date' as index
    df_dsa.set_index('date', inplace=True)

    # Resample the data based on the sample rate, and provide the column names for the new columns
    if quantity_sales_radio == 'quantity':
        prefix = 'orders'
    else:
        prefix = 'sum_sales'
    if sample_rate_dict[time_window] == 'D':
        column_name= prefix + '_3_months'
        agg_data = df_agg_daily_3months
    elif sample_rate_dict[time_window] == 'W-Mon':
        column_name = prefix + '_1_year'
        agg_data= df_agg_weekly_year
    else:
        column_name = prefix + '_1_year'
        agg_data = df_agg_monthly_3years

    fig_tree=px.treemap(df_tree_map,path=['channel', 'region', 'level_1','level_2','sku'],  color='sku', values=column_name)
    fig_tree.update_layout(title=f'Sum of {quantity_sales_radio} by Categories', xaxis_title='Date', yaxis_title=quantity_sales_radio, height=600)

    top_skus = df_sku_sum.nlargest(min(num_skus, n_largest),quantity_sales_radio)['sku']
    agg_data_top_skus = agg_data[agg_data['sku'].isin(top_skus)]
    # Create a bar chart with the filtered data
    fig_bar = px.bar(agg_data_top_skus, x='date', y=prefix, color='sku', title=f'Sum of {quantity_sales_radio} for SKUs')
    analysis_table = dash_table.DataTable(
        id='analysis-table',
        columns=[{"name": i, "id": i} for i in df_tree_map.columns],
        data=df_tree_map.to_dict('records'),
        page_size=30,
        style_table={'overflowX': 'auto'},
        sort_action="native",
        sort_mode="multi",
    )
    if graph_data_tab == 'da-tab-1':
        return html.Div([
            dcc.Graph(id='historical-tree-map', figure=fig_tree),
            html.Hr(),
            dcc.Graph(id='historical-bar-chart', figure=fig_bar), html.Hr()
            ],className='col')
    else:
        return html.Div([  # Forecast Data Table
            analysis_table,
            html.A('Download CSV', id='download-button-analysis', className='btn btn-primary', download="treemap.csv",
                   href="",
                   target="_blank"),
        ])
# return html.Div([dcc.Graph(id='historical-tree-map', figure=fig_tree), html.Hr(),
#                 dcc.Graph(id='historical-bar-chart', figure=fig_bar), html.Hr()
#                 ],className='col')

@app.callback(
    Output('download-button-analysis', 'href'),
    Input('analysis-table', 'data'))
def update_download_link(data):
    df_to_download = pd.DataFrame.from_records(data)
    csv_string = df_to_download.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string



