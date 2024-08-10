import pandas as pd
import numpy as np
from dash import Input, Output, State, dcc, html
from xiom_optimized.app_config_initial import app
from xiom_optimized.caching import (cache, TIMEOUT, df_sales, df_price_sensing_tab as df_price_elasticity, df_price_rec as df_price_recommender,
                                    df_price_rec_summary as df_price_recommender_summary,
                                    df_running_stock as df_stock_forecast,
                                    df_daily_sales_da)
from prophet import Prophet
import plotly.graph_objs as go

@app.callback(
    Output('demand-forecasting-graph', 'children'),
    Output('price-elasticity-graph', 'children'),
    Output('stock-forecasting-graph', 'children'),
    Output('price-recommender-graph', 'children'),
    Input('sku-dropdown', 'value'),
    Input('seasonality-mode-radio', 'value'),
    Input('filter-data', 'data')
)
def update_product_research_graphs(selected_sku, seasonality_mode, filter_data):
    if not selected_sku:
        return html.Div(), html.Div(), html.Div(), html.Div()
    
    # Filter data based on selected SKU
    filtered_data = pd.read_json(filter_data, orient='split')
    df_ds = filtered_data[filtered_data['sku'] == selected_sku].copy()
    
    # Demand Forecasting
    df_ds['date'] = pd.to_datetime(df_ds['date'], errors='coerce')
    df_ds = df_ds.set_index('date')
    df_ds = df_ds.resample('D').sum().reset_index().rename(columns={'date': 'ds', 'quantity': 'y'})

    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False,
                    seasonality_mode=seasonality_mode)
    model.fit(df_ds)
    future = model.make_future_dataframe(periods=365)
    forecast = model.predict(future)

    fig_demand = go.Figure()
    fig_demand.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds['y'], name='Actual'))
    fig_demand.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name='Forecast'))
    fig_demand.update_layout(title='Demand Forecasting', xaxis_title='Date', yaxis_title='Quantity')

    # Price Elasticity
    df_pe = df_price_elasticity[df_price_elasticity['sku'] == selected_sku]
    fig_pe = go.Figure()
    fig_pe.add_trace(go.Scatter(x=df_pe['price'], y=df_pe['quantity'], mode='markers', name='Price Elasticity'))
    fig_pe.update_layout(title='Price Elasticity', xaxis_title='Price', yaxis_title='Quantity')

    # Stock Forecasting
    df_sf = df_stock_forecast[df_stock_forecast['sku'] == selected_sku]
    fig_sf = go.Figure()
    fig_sf.add_trace(go.Scatter(x=df_sf['date'], y=df_sf['stock'], name='Stock Forecast'))
    fig_sf.update_layout(title='Stock Forecasting', xaxis_title='Date', yaxis_title='Stock')

    # Price Recommender
    df_pr = df_price_recommender[df_price_recommender['sku'] == selected_sku]
    fig_pr = go.Figure()
    fig_pr.add_trace(go.Scatter(x=df_pr['date'], y=df_pr['price'], name='Price Recommender'))
    fig_pr.update_layout(title='Price Recommender', xaxis_title='Date', yaxis_title='Price')

    return dcc.Graph(figure=fig_demand), dcc.Graph(figure=fig_pe), dcc.Graph(figure=fig_sf), dcc.Graph(figure=fig_pr)


@app.callback(
    Output('ai-response', 'children'),
    Input('ai-submit-button', 'n_clicks'),
    State('ai-question', 'value'),
    State('sku-dropdown', 'value')
)
def ask_ai(n_clicks, question, selected_sku):
    if n_clicks is None or not question or not selected_sku:
        return ''

    # Here you would integrate with your AI model to get the response
    # For demonstration, we'll return a placeholder response
    response = f"AI response for SKU {selected_sku}: {question}"

    return response