import urllib
import dash_table
import pandas as pd
from xiom_optimized.app_config_initial import app
from xiom_optimized.data_fetcher import df_running_stock, df_stockout_past, df_price_rec, df_price_rec_summary
from dash import Output, Input, State
from dash import html, dcc
from plotly import graph_objs as go
from plotly.subplots import make_subplots
@app.callback(
    Output('tabs-content-stockout-past', 'children'),
    Input('stockout-tabs-past', 'value'),
    State('filter-data', 'data'))
def update_stockout_container_past(graph_data_tab,filter_data):
    n_largest=10
    filtered_data = pd.DataFrame(filter_data)
    selected_sku = filtered_data['sku'].unique().tolist()

    normalized_stockout = df_stockout_past[df_stockout_past['sku'].isin(selected_sku)]


    pivot_df = normalized_stockout.pivot(index='date', columns='sku', values='gap_e_log10')
    # Create a heatmap using Plotly
    fig_stockout = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='spectral_r'))

    # Increase the height of the figure
    fig_stockout.update_layout(height=600, title_text="Past Stockouts")

    # Add x-axis titles
    fig_stockout.update_xaxes(title_text="Amazon SKU")

    # Add y-axis titles
    stockout_past_table = dash_table.DataTable(
        id='stockout-past-table',
        columns=[{"name": i, "id": i} for i in normalized_stockout.columns],
        data=normalized_stockout.to_dict('records'),
        page_size=12,
        style_table={'overflowX': 'scroll'},
        sort_action="native",
        sort_mode="multi",
        style_cell_conditional=[
            {
                'if': {'column_id': c},
                'textAlign': 'left'
            } for c in ['Date', 'Region']
        ]
    )
    if graph_data_tab == 'sop-tab-1':
        return html.Div([
            dcc.Graph(id='stockout-past-heat-map', figure=fig_stockout),
        ], className='col')
    else:
        return html.Div([  # Forecast Data Table
            html.Div([stockout_past_table]),
            html.A('Download CSV', id='download-button-stockout-past', className='btn btn-primary', download="stock_status_past.csv",
                   href="",
                   target="_blank"),
        ],className='col')
    #return html.Div([dcc.Graph(id='historical-bar-chart', figure=fig_stockout), html.Hr()])

@app.callback(
    Output('download-button-stockout-past', 'href'),
    Input('stockout-past-table', 'data'))
def update_download_link(data):
    df_to_download = pd.DataFrame.from_records(data)
    csv_string = df_to_download.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string
