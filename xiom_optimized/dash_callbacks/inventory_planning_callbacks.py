import logging
import urllib

import dash_table
import pandas as pd
from dash import Input
from dash import Output, State
from dash import dcc
from dash import html
from plotly import graph_objs as go
from plotly.subplots import make_subplots

from config import price_recommendation_settings as pr_cf
from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.cache_manager import cache_decorator
from xiom_optimized.utils.data_fetcher import df_price_rec
from xiom_optimized.utils.data_fetcher import df_price_rec_summary
from xiom_optimized.utils.data_fetcher import df_running_stock


@cache_decorator
@app.callback(
    Output('tabs-content-stockout', 'children'),
    [Input('inventory-status-tabs', 'value'),
     Input('filter-data', 'data'),
     Input('view-toggle', 'value')]  # New input for view toggle
)
def inventory_planning_container(graph_data_tab, filter_data, view):
    df_price_rec_summary_filtered=pd.DataFrame()
    if graph_data_tab == 'is-tab-1':
        filtered_data = pd.read_json(filter_data, orient='split')
        unique_wh = filtered_data['warehouse_code'].unique()
        top_n = 50

        df_running_stock_filtered = df_running_stock[df_running_stock['warehouse_code'].isin(unique_wh)]

        # Revenue Impact (Stockout) Graphs
        df_running_stock_us = df_running_stock_filtered[df_running_stock_filtered.is_understock == True]. \
            groupby(['sku', 'warehouse_code'])[['revenue']].sum().reset_index()
        top_stockouts = df_running_stock_us.sort_values(by=['revenue'], ascending=False).head(top_n)
        total_stockout_loss = df_running_stock_us['revenue'].sum()
        total_stockout_loss_formatted = "{:,.0f}".format(total_stockout_loss)

        fig_stockout = go.Figure(go.Bar(
            x=top_stockouts['revenue'],
            y=top_stockouts['sku'] + ' - ' + top_stockouts['warehouse_code'],
            orientation='h',
            marker=dict(color=top_stockouts['revenue'], colorscale='RdBu')
        ))
        fig_stockout.update_layout(
            title='Top Stockout Items by Revenue Loss',
            xaxis_title=f'Loss= {total_stockout_loss_formatted}',
            yaxis_title='SKU - Warehouse Code',
            xaxis_side="top",
            yaxis=dict(autorange="reversed"),
            height=top_n * 22
        )

        df_running_stock_os = df_running_stock_filtered[df_running_stock_filtered.is_overstock == True]
        df_running_stock_os_quantity = df_running_stock_os.sort_values(['sku', 'warehouse_code', 'ds'], ascending=False). \
            groupby(['sku', 'warehouse_code'])[['ds']].first().reset_index()
        df_running_stock_os = pd.merge(df_running_stock_os, df_running_stock_os_quantity, how='inner',
                                       on=['sku', 'warehouse_code', 'ds'])
        avg_yhat = df_running_stock_filtered.groupby(['sku', 'warehouse_code'])['yhat'].mean().reset_index()
        df_running_stock_os = pd.merge(df_running_stock_os, avg_yhat, on=['sku', 'warehouse_code'], suffixes=('', '_avg'))

        df_running_stock_os['over_stocked_quantity'] = (
                df_running_stock_os['running_stock_after_forecast'] -
                df_running_stock_os['yhat_avg'] * (pr_cf.forecast_stock_level + 60))

        df_running_stock_os['over_stocked_revenue_loss'] = df_running_stock_os['over_stocked_quantity'] * (
            df_running_stock_os['price'])
        df_running_stock_os = df_running_stock_os[df_running_stock_os['over_stocked_revenue_loss'].notna()]
        df_running_stock_os = df_running_stock_os[df_running_stock_os['over_stocked_revenue_loss'] != float('inf')]
        df_running_stock_os = df_running_stock_os.groupby(['sku', 'warehouse_code'])[
            ['over_stocked_revenue_loss']].sum().reset_index()
        top_overstock = df_running_stock_os.sort_values(by=['over_stocked_revenue_loss'], ascending=False).head(top_n)
        top_overstock = top_overstock[top_overstock['over_stocked_revenue_loss'] > 0]

        total_overstock_loss = df_running_stock_os['over_stocked_revenue_loss'].sum()
        total_overstock_loss_formatted = "{:,.0f}".format(total_overstock_loss)
        top_overstock['sku'] = top_overstock['sku'] + ' - ' + top_overstock['warehouse_code']

        fig_overstock = go.Figure(go.Bar(
            x=top_overstock['over_stocked_revenue_loss'],
            y=top_overstock['sku'],
            orientation='h',
            marker=dict(color=top_overstock['over_stocked_revenue_loss'], colorscale='Reds')
        ))
        fig_overstock.update_layout(
            title='Top Overstocked Items by Revenue Loss',
            xaxis_title=f'Loss = {total_overstock_loss_formatted}',
            yaxis_title='SKU - Warehouse Code',
            xaxis_side="top",
            yaxis=dict(autorange="reversed"),
            height=top_n * 22
        )

        df_price_rec_summary_filtered = df_price_rec_summary[df_price_rec_summary['warehouse_code'].isin(unique_wh)]
        # Inventory Order Graphs
        df_price_rec_summary_filtered['inventory_order'] = df_price_rec_summary_filtered['inventory_orders'].astype(float)
        positive_inventory = df_price_rec_summary_filtered[df_price_rec_summary_filtered['inventory_orders'] > 0].sort_values(by='inventory_order', ascending=False).head(top_n)
        negative_inventory = df_price_rec_summary_filtered[df_price_rec_summary_filtered['inventory_orders'] < 0].sort_values(by='inventory_order', ascending=True).head(top_n)

        fig_positive_inventory = go.Figure(go.Bar(
            x=positive_inventory['inventory_order'],
            y=positive_inventory['sku'] + ' - ' + positive_inventory['warehouse_code'],
            orientation='h',
            marker=dict(color=positive_inventory['inventory_order'], colorscale='Greens')
        ))
        fig_positive_inventory.update_layout(
            title='Inventory To Order',
            xaxis_title='Order Quantity',
            yaxis_title='SKU - Warehouse Code',
            xaxis_side="top",
            yaxis=dict(autorange="reversed"),
            height=top_n * 22
        )

        fig_negative_inventory = go.Figure(go.Bar(
            x=negative_inventory['inventory_order'],
            y=negative_inventory['sku'] + ' - ' + negative_inventory['warehouse_code'],
            orientation='h',
            marker=dict(color=negative_inventory['inventory_order'], colorscale='Reds')
        ))
        fig_negative_inventory.update_layout(
            title='Slow Moving/ Excessive Inventory ',
            xaxis_title='Inventory Overstock',
            yaxis_title='SKU - Warehouse Code',
            xaxis_side="top",
            yaxis=dict(autorange="reversed"),
            height=top_n * 22
        )

        if view == 'revenue':
            return html.Div([
                html.Div([
                    dcc.Graph(id='top-n-so-graph', figure=fig_stockout)
                ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'}),
                html.Div([
                    dcc.Graph(id='bottom-n-so-graph', figure=fig_overstock)
                ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'})
            ])
        elif view == 'inventory':
            return html.Div([
                html.Div([
                    dcc.Graph(id='positive-inventory-graph', figure=fig_positive_inventory)
                ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'}),
                html.Div([
                    dcc.Graph(id='negative-inventory-graph', figure=fig_negative_inventory)
                ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'})
            ])
        elif view == 'stock_days':
            # Prepare data for understock graph
            stock_days_data = df_price_rec_summary_filtered
            stock_days_data['stock_days'] = df_price_rec_summary_filtered['current_stock']/df_price_rec_summary_filtered['mean_demand']
            understock_data = stock_days_data[stock_days_data['stock_days'] < 120]
            understock_data = understock_data.sort_values(by='stock_days', ascending=True).head(top_n)

            # How to annotate the 0 values?

            fig_understock = go.Figure(go.Bar(
                x=understock_data['stock_days'],
                y=understock_data['sku'] + ' - ' + understock_data['warehouse_code'],
                orientation='h',
                marker=dict(color=understock_data['stock_days'], colorscale='Oranges')
            ))

            # Add annotations for 0 values
            for index, row in understock_data.iterrows():
                if row['stock_days'] == 0:
                    fig_understock.add_annotation(
                        x=row['stock_days'],
                        y=row['sku'] + ' - ' + row['warehouse_code'],
                        text="0",
                        showarrow=True,
                        arrowhead=2,
                        ax=20,
                        ay=0
                    )

            fig_understock.update_layout(
                title='How many days of stock do you have?',
                xaxis_title='Days of Stock',
                yaxis_title='SKU - Warehouse Code',
                xaxis_side="top",
                yaxis=dict(autorange="reversed"),
                height=top_n * 22
            )
            # Prepare data for overstock graph
            overstock_data = stock_days_data[stock_days_data['stock_days'] > 180]
            overstock_data['overstock_days'] = stock_days_data['stock_days'] - 180
            overstock_data = overstock_data.sort_values(by='stock_days', ascending=False).head(top_n)

            fig_overstock = go.Figure(go.Bar(
                x=overstock_data['overstock_days'],
                y=overstock_data['sku'] + ' - ' + overstock_data['warehouse_code'],
                orientation='h',
                marker=dict(color=overstock_data['overstock_days'], colorscale='Blues')
            ))
            fig_overstock.update_layout(
                title='How many days of overstock do you have?',
                xaxis_title='Excess Days of Stock, 180 days is the optimal stock level',
                yaxis_title='SKU - Warehouse Code',
                xaxis_side="top",
                yaxis=dict(autorange="reversed"),
                height=top_n * 22
            )

            return html.Div([
                html.Div([
                    dcc.Graph(id='understock-days-graph', figure=fig_understock)
                ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'}),
                html.Div([
                    dcc.Graph(id='overstock-days-graph', figure=fig_overstock)
                ], style={'overflow-y': 'auto', 'display': 'inline-block', 'width': '50%', 'height': '500px'})
            ])
    elif graph_data_tab == 'is-tab-2': #add dash.table for price recommendation here
        filtered_data = pd.read_json(filter_data, orient='split')
        unique_wh = filtered_data[['sku', 'warehouse_code']].drop_duplicates()
        df_table=df_price_rec_summary.merge(unique_wh, on=['sku','warehouse_code'], how='inner')
        top_n = 50
        pr_table = dash_table.DataTable(
            id='pr-summary-table',
            columns=[{"name": i, "id": i} for i in df_table.columns],
            data=df_table.head(100).to_dict('records'),
            page_size=10,
            sort_action="native",
            sort_mode="multi",
            style_cell_conditional=[
                {
                    'if': {'column_id': c},
                    'textAlign': 'left'
                } for c in ['Date', 'Region']
            ])

        return html.Div([  # Forecast Data Table
            html.Div([pr_table], className="col-md-12"),
            html.Button(children="Download Data",id='download-button-inventory',className='btn btn-primary'),
            dcc.Download(id="download-pr-data"),
        ], className="col-md-12")


@app.callback(
    Output('download-pr-data', 'data'),
    Input('download-button-inventory', 'n_clicks'),
    State('filter-data', 'data'),
    prevent_initial_call=True
)
def update_download_link(n_clicks,filter_data):
    filtered_data = pd.read_json(filter_data, orient='split')
    unique_wh = filtered_data[['sku','warehouse_code']].drop_duplicates()
    df_to_download = df_price_rec_summary.merge(unique_wh, on=['sku','warehouse_code'])
    return dcc.send_data_frame(df_to_download.to_csv, "price_recommendation_summary.csv")


@app.callback(
    Output('tabs-content-sss', 'children'),
    [Input('sss-tabs', 'value'),
     Input('sku-dropdown', 'value'),
     Input('warehouse-code-dropdown', 'value'),
    Input('filter-data', 'data')],
)
def update_pr_container(graph_data_tab, selected_sku, selected_warehouse_code, filter_data):
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
        title=f"""Price : {price_old:.02f} Revenue:  {revenue_before:.0f}""",
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
        title=f"""Price Recommendation: {price_new:.02f} Revenue:  {revenue_after:.02f}""",
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

    filtered_data = pd.read_json(filter_data, orient='split')
    unique_wh = filtered_data[['sku', 'warehouse_code']].drop_duplicates()
    df_table = df_price_rec.merge(unique_wh, on=['sku', 'warehouse_code'], how='inner')
    # price recommendation table working
    pr_table = dash_table.DataTable(
        id='pr-table',
        columns=[{"name": i, "id": i} for i in df_table.columns],
        data=df_table.head(100).to_dict('records'),
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
            pr_table,
            html.Button('Download CSV', id='download-button-pr-date',className='btn btn-primary'),
            dcc.Download(id="download-pr-date-data"),
        ])


@app.callback(
    Output('downloand-pr-date-data', 'data'),
    Input('download-button-pr-date', 'n_clicks'),
    State('filter-data', 'data'),
    prevent_initial_call=True
)
def update_download_link(n_clicks,filter_data):
    if n_clicks is None:
        return
    filtered_data = pd.read_json(filter_data, orient='split')
    unique_wh = filtered_data[['sku', 'warehouse_code']].drop_duplicates()
    df_to_download = df_price_rec.merge(unique_wh, on=['sku', 'warehouse_code'])
    return dcc.send_data_frame(df_to_download.to_csv, "pr_running_stock.csv")
