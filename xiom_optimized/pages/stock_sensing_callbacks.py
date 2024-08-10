import urllib
import dash_table
import pandas as pd
from xiom_optimized.app_config_initial import app
from xiom_optimized.caching import df_running_stock, df_stockout_past ,df_price_rec, df_price_rec_summary
from dash import Output, Input, State
from dash import html, dcc
from plotly import graph_objs as go
from plotly.subplots import make_subplots

from dash import dcc
from dash import html
import logging


@app.callback(
    Output('tabs-content-stockout', 'children'),
    Input('stockout-tabs', 'value'),
    State('filter-data', 'data'))
def update_stockout_container(graph_data_tab,filter_data):
    top_n = 100

    # find the top 10 SKUs with the highest stockout loss
    df_running_stock_us = df_running_stock[df_running_stock.is_understock == True]. \
        groupby(['sku', 'warehouse_code'])[['revenue']].sum().reset_index()
    top_stockouts = df_running_stock_us.sort_values(by=['revenue'], ascending=False).head(top_n)
    total_stockout_loss = df_running_stock_us['revenue'].sum()
    total_stockout_loss_fomatted = "{:,.0f}".format(total_stockout_loss)

    #get sku and warehouse code together in a string for top stockouts
    top_stockouts['sku'] = top_stockouts['sku'] + ' - ' + top_stockouts['warehouse_code']
    # find the top 10 SKUs with the highest overstock loss
    # Stockout Plot
    fig_stockout = go.Figure(go.Bar(
        x=top_stockouts['revenue'],
        y=top_stockouts['sku'],
        orientation='h',
        marker=dict(
            color=top_stockouts['revenue'],
            colorscale='RdBu',  # or any other color scale that you prefer
        )
    ))
    fig_stockout.update_layout(
        title='Top Stockout Items by Revenue Loss',
        xaxis_title=f'Loss= {total_stockout_loss_fomatted}',
        yaxis_title='SKU - Warehouse Code ',
        xaxis_side="top",
        yaxis=dict(autorange="reversed"),  # To display top items at top
        height=800
    )

    df_running_stock_os = df_running_stock[df_running_stock.is_overstock == True]
    df_running_stock_os_quantity = df_running_stock_os.sort_values(['sku', 'warehouse_code', 'ds'], ascending=False). \
        groupby(['sku', 'warehouse_code'])[['ds']].first().reset_index()
    df_running_stock_os = pd.merge(df_running_stock_os, df_running_stock_os_quantity, how='inner',
                                   on=['sku', 'warehouse_code', 'ds'])
    df_running_stock_os['over_stocked_quantity'] = df_running_stock_os['running_stock_after_forecast'] - \
                                                   df_running_stock_os['yhat'] * 180

    df_running_stock_os['over_stocked_revenue_loss'] = df_running_stock_os['over_stocked_quantity'] * (
    df_running_stock_os['price'])
    # filter nan and inf values
    df_running_stock_os = df_running_stock_os[df_running_stock_os['over_stocked_revenue_loss'].notna()]
    df_running_stock_os = df_running_stock_os[df_running_stock_os['over_stocked_revenue_loss'] != float('inf')]

    top_overstock = df_running_stock_os.sort_values(by=['over_stocked_revenue_loss'], ascending=False).head(top_n)
    total_overstock_loss = df_running_stock_os['over_stocked_revenue_loss'].sum()
    total_overstock_loss_formatted = "{:,.0f}".format(total_overstock_loss)
    top_overstock['sku'] = top_overstock['sku'] + ' - ' + top_overstock['warehouse_code']
    # Overstock Plot
    fig_overstock = go.Figure(go.Bar(
        x=top_overstock['over_stocked_revenue_loss'],
        y=top_overstock['sku'],
        orientation='h',
        marker=dict(
            color=top_overstock['over_stocked_revenue_loss'],
            colorscale='Reds',  # or any other color scale that you prefer
        )
    ))
    fig_overstock.update_layout(
        title='Top Overstocked Items by Revenue Loss',
        xaxis_title=f'Loss = {total_overstock_loss_formatted}',
        yaxis_title='SKU - Warehouse Code',
        xaxis_side="top",
        yaxis=dict(autorange="reversed"),  # To display top items at top
        height=800
    )
    download_columns = ['sku', 'ds', 'warehouse_code', 'yhat', 'running_stock_after_forecast', 'InTransit_Quantity']
    # Add x-axis titles
    # Add y-axis titles
    stockout_table = dash_table.DataTable(
        id='stockout-table',
        columns=[{"name": i, "id": i} for i in download_columns],
        data=df_running_stock[download_columns].to_dict('records'),
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
    if graph_data_tab == 'so-tab-1':
        return html.Div([
            html.Div([
                dcc.Graph(id='top-n-so-graph', figure=fig_stockout)
            ], style={'overflow-y': 'auto',  'display': 'inline-block', 'width': '50%', 'height': '500px'}),

            html.Div([
                dcc.Graph(id='bottom-n-so-graph', figure=fig_overstock)
            ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'})
        ])
    else:
        return html.Div([  # Forecast Data Table
            stockout_table,
            html.A('Download CSV', id='download-button-stockout', className='btn btn-primary', download="stock_status.csv",
                   href="",
                   target="_blank"),
        ], style={'overflow-y': 'scroll', 'overflowX': 'scroll', 'width':'100%'})
    #return html.Div([dcc.Graph(id='historical-bar-chart', figure=fig_stockout), html.Hr()])
@app.callback(
    Output('download-button-stockout', 'href'),
    Input('stockout-table', 'data'))
def update_download_link(data):
    df_to_download = pd.DataFrame.from_records(data)
    csv_string = df_to_download.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string


@app.callback(
    Output('tabs-content-sss', 'children'),
    [Input('sss-tabs', 'value'),
     Input('sku-dropdown', 'value'),
     Input('warehouse-code-dropdown', 'value')])
def update_pr_container(graph_data_tab, selected_sku, selected_warehouse_code):
    if not selected_sku:
        selected_sku = 'WAN-W1B+'
    if not selected_warehouse_code:
        selected_warehouse_code = 'US'

    sku_df = df_running_stock[
        (df_running_stock['sku'] == selected_sku) & (df_running_stock['warehouse_code'] == selected_warehouse_code)]
    sku_df = sku_df.sort_values('ds')

    # Create subplots: two rows, one column
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.1)

    # Add running_stock_after_forecast to the first row
    fig.add_trace(
        go.Scatter(x=sku_df['ds'], y=sku_df['running_stock_after_forecast'],
                   name='Running Stock After Forecast', mode='lines', line=dict(color='green')),
        row=1, col=1
    )

    # Add yhat (Forecasted daily sales) as bars to the second row with color scale
    fig.add_trace(
        go.Bar(x=sku_df['ds'], y=sku_df['yhat'], name='Forecasted daily sales',
               marker=dict(color=sku_df['yhat'], colorscale='Blues')),
        row=2, col=1
    )

    # Calculate the maximum values for each y-axis
    max_yhat = sku_df['yhat'].max()
    max_running_stock = sku_df['running_stock_after_forecast'].max()

    # Set the y-axis ranges independently
    fig.update_yaxes(range=[0, max_running_stock], row=1, col=1)  # First row for running stock
    fig.update_yaxes(range=[0, max_yhat], row=2, col=1)  # Second row for daily sales

    # Add vertical lines and annotations for Expected Arrival Dates
    for _, row in sku_df.dropna(subset=['Expected_Arrival_Date']).iterrows():
        fig.add_vline(x=row['Expected_Arrival_Date'], line=dict(color='red', dash='dash'), line_width=1, row=1, col=1)
        fig.add_annotation(x=row['Expected_Arrival_Date'], y=max_running_stock / 2,
                           text=str(int(row['InTransit_Quantity'])),
                           showarrow=False, font=dict(color='red'), row=1, col=1)

    sku_price_summary = df_price_rec_summary[(df_price_rec_summary['sku'] == selected_sku) & (
                df_price_rec_summary['warehouse_code'] == selected_warehouse_code)]

    # Check if sku_price_summary is empty
    if sku_price_summary.empty:
        price_old = 0
        revenue_before = 0
    else:
        price_old = sku_price_summary['price_old'].iloc[0]
        revenue_before = sku_price_summary['revenue_before'].iloc[0]

    # Update layout
    fig.update_layout(
        autosize=True,
        title=f"""Price : {price_old:.0f} Revenue:  {revenue_before:.0f}""",
        xaxis_title=f'Stock Status for SKU {selected_sku} at Warehouse {selected_warehouse_code}',
        yaxis_title='Running Stock After Forecast',
        yaxis2_title='Forecasted daily sales',
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600
    )

    # Update y-axes titles
    fig.update_yaxes(title_text='Running Stock After Forecast', row=1, col=1, color='green')
    fig.update_yaxes(title_text='Forecasted Daily sales', row=2, col=1, color='blue')

    logging.info(f"df_price_rec_summary: {df_price_rec.head()}")

    sku_df_pr = df_price_rec[
        (df_price_rec['sku'] == selected_sku) & (df_price_rec['warehouse_code'] == selected_warehouse_code)]
    sku_df_pr = sku_df_pr.sort_values('ds')

    # Create subplots: two rows, one column
    fig_pr = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.1)

    # Add running_stock_after_forecast_adj to the first row
    fig_pr.add_trace(
        go.Scatter(x=sku_df_pr['ds'], y=sku_df_pr['running_stock_after_forecast_adj'],
                   name='Running Stock After Adj Forecast', mode='lines', line=dict(color='green')),
        row=1, col=1
    )

    # Add q_prime_adj (Forecasted daily sales) as bars to the second row with a different color scale
    fig_pr.add_trace(
        go.Bar(x=sku_df_pr['ds'], y=sku_df_pr['q_prime_adj'], name='Forecasted daily sales',
               marker=dict(color=sku_df_pr['q_prime_adj'], colorscale='Reds')),
        row=2, col=1
    )

    # Calculate the maximum values for each y-axis
    max_q_prime_adj = sku_df_pr['q_prime_adj'].max()
    max_running_stock_adj = sku_df_pr['running_stock_after_forecast_adj'].max()

    # Set the y-axis ranges independently
    fig_pr.update_yaxes(range=[0, max_running_stock_adj], row=1, col=1)  # First row for running stock
    fig_pr.update_yaxes(range=[0, max(max_yhat, max_q_prime_adj)], row=2, col=1)  # Second row for daily sales

    # Add vertical lines and annotations for Expected Arrival Dates
    for _, row in sku_df_pr[sku_df_pr['InTransit_Quantity'] != 0].iterrows():
        fig_pr.add_vline(x=row['ds'], line=dict(color='red', dash='dash'), line_width=1, row=1, col=1)
        fig_pr.add_annotation(x=row['ds'], y=max_running_stock_adj / 2, text=str(int(row['InTransit_Quantity'])),
                              showarrow=False, font=dict(color='red'), row=1, col=1)

    # Check if sku_price_summary is empty
    if sku_price_summary.empty:
        price_new = 0
        revenue_after = 0
    else:
        price_new = sku_price_summary['price_new'].iloc[0]
        revenue_after = sku_price_summary['revenue_after'].iloc[0]

    # Update layout
    fig_pr.update_layout(
        autosize=True,
        title=f"""Price Recommendation: {price_new:.0f} Revenue:  {revenue_after:.0f}""",
        xaxis_title=f'Stock Status for SKU {selected_sku} at Warehouse {selected_warehouse_code}',
        yaxis_title='Running Stock After Adj Forecast',
        yaxis2_title='Forecasted daily sales',
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600
    )

    # Update y-axes titles
    fig_pr.update_yaxes(title_text='Running Stock After Adj Forecast', row=1, col=1, color='green')
    fig_pr.update_yaxes(title_text='Forecasted Daily sales', row=2, col=1, color='blue')

    download_columns = ['sku', 'warehouse_code', 'revenue_before', 'revenue_after', 'price_old', 'price_new']

    # price recommendation table working
    pr_table = dash_table.DataTable(
        id='pr-table',
        columns=[{"name": i, "id": i} for i in download_columns],
        data=df_price_rec_summary[download_columns].to_dict('records'),
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
    if graph_data_tab == 'pr-tab-1':
        return html.Div([
            html.Div([
                dcc.Graph(id='top-n-pr-graph', figure=fig)
            ], style={'display': 'inline-block', 'width': '50%'}),
            html.Div([
                dcc.Graph(id='bottom-n-pr-graph', figure=fig_pr)
            ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%'})
        ])
    else:
        return html.Div([  # Forecast Data Table
            # pr_table,
            html.A('Download CSV', id='download-button-pr', className='btn btn-primary',
                   download="price_recommender.csv",
                   href="",
                   target="_blank"),
        ])

@app.callback(
    Output('download-button-pr', 'href'),
    Input('pr-table', 'data'))
def update_download_link(data):
    df_to_download = pd.DataFrame.from_records(data)
    csv_string = df_to_download.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string