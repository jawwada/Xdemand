import urllib

import dash_table
import pandas as pd
import plotly.express as px
from dash import Input
from dash import Output
from dash import dcc
from dash import html

from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.cache_manager import cache_decorator
from xiom_optimized.utils.config_constants import sample_rate_dict
from xiom_optimized.utils.data_fetcher import df_sales
from xiom_optimized.utils.data_fetcher import ph_data


@cache_decorator
@app.callback(
    Output('da-tabs-content-analysis', 'children'),
    Input('quantity-sales-radio', 'value'),
    Input('sample-rate-slider', 'value'),
    Input('analysis-tabs', 'value'),
    Input('filter-data', 'data'))
def update_demand_analysis_graph(quantity_sales_radio, time_window, graph_data_tab, filtered_data):
    max_date = df_sales['date'].max()
    max_date = max_date - pd.DateOffset(weeks=1)
    min_date = max_date - pd.DateOffset(months=12)
    df_lastyear = df_sales[(df_sales['date'] < max_date) & (df_sales['date'] > min_date)].copy(deep=True)

    df_lastyear = df_lastyear.groupby([
        'sku',
        'region',
        'channel',
        'warehouse_code',
        'level_1',
        pd.Grouper(freq=sample_rate_dict[time_window], key='date')]).agg({
        quantity_sales_radio: 'sum',
        'price': 'mean'}).reset_index()
    filtered_data = pd.read_json(filtered_data, orient='split') # drop duplicates otherwise big erros
    filtered_data = filtered_data[['channel','sku', 'warehouse_code', 'region', 'level_1']].drop_duplicates()
    df_sales_filtered = pd.merge(df_lastyear, filtered_data, on=['channel','sku', 'warehouse_code', 'region', 'level_1'],
                                 how='inner')

    if graph_data_tab == 'da-tab-1':
        n_largest = 10
        # Filter the data to past 12 months
        # Filter the data to past 12 months

        df_sales_filtered['sku_warehouse'] = df_sales_filtered['sku'] + " " + df_sales_filtered['warehouse_code']
        # group by montly data and take only complete months

        df = df_sales_filtered[['sku_warehouse', 'date', quantity_sales_radio]].copy(deep=True)
        # sample the data frame by month and sum by the quantity_sales_radio

        df = df.groupby(['sku_warehouse', 'date'])[quantity_sales_radio].sum().reset_index()
        df_month1 = df[df['date'] > max_date - pd.DateOffset(months=1)]. \
            groupby(['sku_warehouse'])[quantity_sales_radio].sum().reset_index()
        df_month1_prev_year = df[df['date'] > max_date - pd.DateOffset(months=12)]. \
            groupby(['sku_warehouse'])[quantity_sales_radio].sum().reset_index()

        df_month1['mom_change'] = (df_month1[quantity_sales_radio] - df_month1_prev_year[quantity_sales_radio]) / \
                                  df_month1_prev_year[quantity_sales_radio]

        df_month1.sort_values('mom_change', ascending=False, inplace=True)
        df_month1 = df_month1[['sku_warehouse','mom_change']].drop_duplicates()
        df = pd.merge(df, df_month1[['sku_warehouse', 'mom_change']], on='sku_warehouse', how='left')
        winners = pd.merge(df, df_month1['sku_warehouse'].head(n_largest), on='sku_warehouse', how='inner')
        losers = pd.merge(df, df_month1['sku_warehouse'].tail(n_largest), on='sku_warehouse', how='inner')
        # Create time series graphs for winners, losers, and laggards
        fig_winners = px.bar(winners, x='date', y=quantity_sales_radio, color='sku_warehouse',
                             title='Growth Drivers - MoM Change')
        fig_losers = px.bar(losers, x='date', y=quantity_sales_radio, color='sku_warehouse',
                            title='Losers - MoM Change')

        df = df_sales_filtered[['region', 'date', quantity_sales_radio]].copy(deep=True)
        regions = df['region'].unique()

        df = df.groupby(['region', 'date'])[quantity_sales_radio].sum().reset_index()
        fig_region = px.line(df, x='date', y=quantity_sales_radio, color='region', title='Regional Trends')

        df_category = pd.merge(df_lastyear[['date', 'sku', quantity_sales_radio]].drop_duplicates()
                               , ph_data[['sku', 'level_1']].drop_duplicates(),
                               on=['sku'], how='left')
        df_category = df_category.groupby(['date', 'level_1'])[quantity_sales_radio].sum().reset_index()
        fig_category = px.line(df_category, x='date', y=quantity_sales_radio, color='level_1', title='Category Trends')

        df_tree_map = (
            df_sales_filtered.groupby([
                'channel',
                'region',
                'sku'
            ])
            [[quantity_sales_radio]]
            .sum()
            .reset_index()
        )
        # Convert the 'date' column back to datetime (from Period)

        df_tree_map = pd.merge(df_tree_map, ph_data[['channel', 'sku', 'region']].drop_duplicates(),
                               on=['channel', 'sku', 'region'], how='left')
        # Create the treemap
        df_tree_map = df_tree_map.groupby(['channel', 'region', 'sku'])[
            quantity_sales_radio].sum().reset_index()
        fig_tree = px.treemap(df_tree_map, path=['channel', 'region', 'sku'],
                              color='sku', values=quantity_sales_radio, title='Sales')

        num_skus = len(df_tree_map['sku'].unique())
        df_sku_sum = df_sales_filtered.groupby(['sku'])[[quantity_sales_radio]].sum().reset_index()
        top_skus = df_sku_sum.nlargest(min(num_skus, n_largest), quantity_sales_radio)['sku']
        agg_data_top_skus = df_lastyear[df_lastyear['sku'].isin(top_skus)]
        fig_bar = px.bar(agg_data_top_skus, x='date', y=quantity_sales_radio, color='sku', \
                         title=f'Top Earners - {quantity_sales_radio.capitalize()}')

        return html.Div([
            html.Div([
                html.Div(dcc.Graph(id='historical-tree-map', figure=fig_tree), className='col-md-6'),
                html.Div(dcc.Graph(id='historical-region', figure=fig_region), className='col-md-6'),
            ], className='row'),

            html.Hr(),
            html.Div([
                html.Div(dcc.Graph(id='historical-winners', figure=fig_winners), className='col-md-6'),
                html.Div(dcc.Graph(id='losers-time-series', figure=fig_losers), className='col-md-6')
            ], className='row'),

            html.Hr(),
            html.Div([
                html.Div(dcc.Graph(id='category-trends', figure=fig_category), className='col-md-6'),
                html.Div(dcc.Graph(id='historical-bar-chart', figure=fig_bar), className='col-md-6'),
            ], className='row'),
        ], className='col-md-12')
    else:
        analysis_table = dash_table.DataTable(
            id='analysis-table',
            columns=[{"name": i, "id": i} for i in df_sales_filtered.columns],
            data=df_sales_filtered.head(100).to_dict('records'),
            page_size=20,
            style_table={'className': 'col-md-12'},
            sort_action="native",
            sort_mode="multi",
        )
        return html.Div([  # Forecast Data Table
            analysis_table,
            html.A('Download CSV', id='download-button-analysis', className='btn btn-primary', download="analysis.csv",
                   href="",
                   target="_blank"),
        ])


@app.callback(
    Output('download-button-analysis', 'href'),
    Input('analysis-table', 'data'))
def update_download_link(data):
    df_to_download = pd.DataFrame.from_records(data)
    csv_string = df_to_download.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string
