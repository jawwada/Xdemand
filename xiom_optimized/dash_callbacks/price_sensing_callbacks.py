import dash_table
import pandas as pd
import plotly.express as px
from dash import Input
from dash import Output, State
from dash import dcc
from dash import html
from plotly import graph_objs as go
from plotly.subplots import make_subplots

from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.cache_manager import cache_decorator
from xiom_optimized.utils.data_fetcher import df_daily_sales_da
from xiom_optimized.utils.data_fetcher import df_price_regression_tab
from xiom_optimized.utils.data_fetcher import df_price_sensing_tab


@cache_decorator
@app.callback(
    Output('ps-tabs-content', 'children'),
    Input('ps-tabs', 'value'),
    Input('filter-data', 'data')
)
def update_price_sensing_graph(graph_data_tab, filter_data):
    filtered_data = pd.read_json(filter_data, orient='split')
    unique_wh = filtered_data['warehouse_code'].unique()
    if isinstance(unique_wh, str):
        unique_wh = [unique_wh]

    df = df_price_sensing_tab[df_price_sensing_tab['warehouse_code'].isin(unique_wh)]
    df['sku_warehouse'] = df['sku'] + " " + df['warehouse_code']

    if graph_data_tab == 'ps-tab-1':
        # Define the bins and labels
        bins = [float('-inf'), -1.75, -1.25, 0]
        labels = ['Highly Elastic', 'Elastic', 'Unitary/Inelastic']

        # sort the data
        df = df.sort_values(by='price_elasticity', ascending=False)

        # Categorize the SKUs based on the price elasticity bins
        df['elasticity_bin'] = pd.cut(df['price_elasticity'], bins=bins, labels=labels)

        # Create a single color scale
        color_scale = 'Turbo'

        # Create a figure for each bin
        figures = []
        for label in labels:
            bin_df = df[df['elasticity_bin'] == label]
            fig = go.Figure(go.Bar(
                x=bin_df['price_elasticity'],
                y=bin_df['sku_warehouse'],
                orientation='h',
                marker=dict(
                    color=bin_df['price_elasticity'],
                    colorscale=color_scale,  # Use the same color scale
                )
            ))
            fig.update_layout(
                title=f'{label}',
                xaxis_side="top",
                height=max(len(bin_df) * 25, 400)  # height should equal the number of SKUs in the bin * 25
            )
            figures.append(fig)

        # Add a single color bar to the first figure
        figures[0].update_layout(
            coloraxis=dict(
                colorscale=color_scale,
                colorbar=dict(title='price_elasticity')
            )
        )

        return html.Div([
            html.Div([
                dcc.Graph(id=f'{label.lower().replace(" ", "-")}-price_elasticity-graph', figure=fig)
            ], style={'overflow-y': 'scroll', 'height': '400px', 'display': 'inline-block', 'width': '30%'})
            for fig, label in zip(figures, labels)
        ])
    else:
        ps_table = dash_table.DataTable(
            id='forecast-table',
            columns=[{"name": i, "id": i} for i in df_price_sensing_tab.columns],
            data=df_price_sensing_tab.to_dict('records'),
            page_size=12,
            style_table={'overflowX': 'auto'},
            sort_action="native",
            sort_mode="multi",
            style_cell_conditional=[
                {
                    'if': {'column_id': c},
                    'textAlign': 'left'
                } for c in ['Date', 'Region']
            ],
        )
        download_button = html.Button("Download Data", id="download-button")
        download_component = dcc.Download(id="download-dataframe-csv")

        return html.Div([  # Forecast Data Table
            ps_table,
            download_button,
            download_component
        ])


@app.callback(
    Output('sku-price-sensing-container', 'children'),
    Input('sku-dropdown', 'value'),
    Input('filter-data', 'data')
)
def update_sku_price_relationship_graph(selected_sku=None, filter_data=None):
    filtered_data = pd.read_json(filter_data, orient='split')
    if selected_sku is None:
        selected_sku = []
    elif isinstance(selected_sku, str):
        selected_sku = [selected_sku]
    else:
        selected_sku = filtered_data['sku'].unique()

    df_sales_filtered = df_daily_sales_da.merge(filtered_data, on=['sku', 'warehouse_code'], how='inner')
    today = pd.to_datetime("today")

    year_ago = today - pd.DateOffset(months=14)
    df_dsa = df_sales_filtered[(df_sales_filtered['date'] >= year_ago) & (df_sales_filtered['sku'].isin(selected_sku))]

    df_dsa['date'] = pd.to_datetime(df_dsa['date'])
    df_dsa.fillna(0, inplace=True)
    df_dsa = df_dsa.groupby([pd.Grouper(key='date', freq='W-Mon')]). \
        agg({'quantity': 'sum', 'revenue': 'sum', 'price': 'mean', 'promotional rebates': 'mean'}).reset_index()
    df_dsa.set_index('date', inplace=True)
    sku = selected_sku
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        subplot_titles=("Main Plot", "Rebates"), row_heights=[0.7, 0.3],
                        specs=[[{"secondary_y": True}], [{}]])

    fig.add_trace(go.Bar(x=df_dsa.index, y=df_dsa['quantity'], name='Quantity'), row=1, col=1, secondary_y=False)
    fig.add_trace(
        go.Scatter(x=df_dsa.index, y=df_dsa['quantity'].rolling(window=4).mean(), mode='lines', name='Trend'), row=1,
        col=1, secondary_y=False)

    fig.add_trace(go.Scatter(x=df_dsa.index, y=df_dsa['price'], mode='lines', name='Price'), row=1, col=1,
                  secondary_y=True)

    fig.add_trace(go.Bar(x=df_dsa.index, y=df_dsa['promotional rebates'], name='Rebates'), row=2, col=1)

    fig.update_layout(title_text=f'Selling Price and Volume Timeline SKU {sku}')
    fig.update_yaxes(title_text="Price", secondary_y=True)
    filtered_pr = pd.merge(df_price_regression_tab, filtered_data, on=['sku', 'warehouse_code'], how='inner')
    filtered_pr = filtered_pr[filtered_pr['sku'].isin(selected_sku)]
    filtered_pr = filtered_pr.groupby(['idx']).agg({'x_pred': 'mean', 'y_pred': 'sum'}).reset_index()

    fig2 = px.scatter(
        filtered_pr,
        x='x_pred',
        y='y_pred',
    )
    fig2.update_layout(
        title='Price Elasticity',
        xaxis_title='Price Quantity Relationship',
        yaxis_title='Quantity'
    )
    return html.Div([
        html.Div([dcc.Graph(id='top-n-skus-graph', figure=fig)
                  ], style={'display': 'inline-block', 'width': '50%'}),
        html.Div([dcc.Graph(id='sku-price-sensing-graph', figure=fig2)
                  ], style={'display': 'inline-block', 'width': '50%'})
    ])


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("download-button", "n_clicks"),
    Input('filter-data', 'data'),
    prevent_initial_call=True,
)
def download_csv(n_clicks, filter_data):
    if n_clicks is None:
        return None
    filtered_data = pd.read_json(filter_data, orient='split')
    unique_wh = filtered_data['warehouse_code'].unique()
    if isinstance(unique_wh, str):
        unique_wh = [unique_wh]

    df = df_price_sensing_tab[df_price_sensing_tab['warehouse_code'].isin(unique_wh)]
    return dcc.send_data_frame(df.to_csv, "price_elasticity_data.csv")
