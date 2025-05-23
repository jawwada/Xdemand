import urllib
from datetime import datetime
from dash import no_update
import dash_table
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from xiom_optimized.app_config_initial import app
from xiom_optimized.caching import cache, df_fc_qp, df_sales
from xiom_optimized.config_constants import  TIMEOUT, sample_rate_dict
from dash import Input, Output, State, dcc, html, dash_table
from plotly.subplots import make_subplots
from prophet import Prophet

@cache.memoize(timeout=TIMEOUT)
@app.callback(
    Output('tabs-content', 'children'),
    Input('quantity-sales-radio', 'value'),
    Input('sample-rate-slider', 'value'),
    Input('demand-tabs', 'value'),
    Input('filter-data', 'data'),
    Input('sku-dropdown', 'value'),
    Input('seasonality-mode-radio', 'value')
)
def update_demand_forecast_graph(quantity_sales_radio,time_window,
                                 graph_data_tab,filter_data,
                                 selected_sku, seasonality_mode):
    if graph_data_tab == 'tab-1':
        if isinstance(selected_sku, str):
            df_ds = df_sales[df_sales['sku'] == selected_sku].copy()

            df_ds['date'] = pd.to_datetime(df_ds['date'], errors='coerce')
            df_ds = df_ds.set_index('date')
            df_ds = df_ds[quantity_sales_radio]

            # Inside your update_demand_forecast_graph function, after you define df_ds and set 'date' as its index:
            # Set specific months to NaN
            df_ds = df_ds.resample(sample_rate_dict[time_window]).sum()

            # Make sure your dataframe is in the right format for Prophet
            df_ds = df_ds.reset_index().rename(columns={'date': 'ds', quantity_sales_radio: 'y'})

            # Initialize the model
            if sample_rate_dict[time_window] == 'D':
                model = Prophet(yearly_seasonality=True,
                                weekly_seasonality=True,
                                daily_seasonality=False,
                                seasonality_mode=seasonality_mode)
            else:
                model = Prophet(yearly_seasonality=True,
                                weekly_seasonality=False,
                                daily_seasonality=False,
                                seasonality_mode=seasonality_mode)

            # Fit the model to your data
            model.fit(df_ds)
            # After fitting the model and making predictions, plot the components

            # Make future predictions
            future = model.make_future_dataframe(periods=365)  # adjust as needed
            forecast = model.predict(future)

            # Create subplots: use 'domain' type for Pie subplot
            fig_components = make_subplots(rows=2, cols=1)
            fig_components.update_layout(title_text="Forecasting Model Components")
            # Add traces
            fig_components.add_trace(go.Scatter(x=forecast['ds'], y=forecast['trend'], name='Trend'), row=1, col=1)

            if model.weekly_seasonality:
                fig_components.add_trace(go.Scatter(x=forecast['ds'], y=forecast['weekly'], name='Weekly'), row=2,
                                         col=1)

            if model.yearly_seasonality:
                fig_components.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yearly'], name='Yearly'), row=2,
                                         col=1)

            # Update layout
            fig_components.update_xaxes(title_text="Date", row=1, col=1)
            fig_components.update_yaxes(title_text="Trend Value", row=1, col=1)

            fig_components.update_xaxes(title_text="Date", row=2, col=1)
            fig_components.update_yaxes(title_text="Seasonality Value", row=2, col=1)
            # Add this figure to your Dash application

            # Adjust forecasted data and confidence intervals to be no lower than 0
            forecast['yhat'] = np.maximum(0, forecast['yhat'])
            forecast['yhat_lower'] = np.maximum(0, forecast['yhat_lower'])
            forecast['yhat_upper'] = np.maximum(0, forecast['yhat_upper'])

            # Create a Dash figure with Plotly
            fig = go.Figure()

            # Add actual data to the figure
            fig.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds['y'], name='Actual'))
            # Add the forecasted data to the figure
            fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], name='Forecast'))

            # Add the forecast components to the figure
            fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat_lower'], name='Lower Bound of Forecast',
                                     line=dict(width=0)))
            fig.add_trace(
                go.Scatter(x=forecast['ds'], y=forecast['yhat_upper'], name='Upper Bound of Forecast', fill='tonexty'))

            fig.update_layout(title=f'RDX Demand Forecast:  sku = {selected_sku} {quantity_sales_radio} ',
                              xaxis_title='Date', yaxis_title=quantity_sales_radio, height=400)

        else:
            df_fc_qp['ds'] = pd.to_datetime(df_fc_qp['ds'])

            # Calculate today's date
            today = pd.to_datetime("today")

            # Calculate the date range (today ± 6 months)
            six_months_ago = today - pd.DateOffset(months=6)
            six_months_later = today + pd.DateOffset(months=5)
            df_fc_qp_filtered = df_fc_qp[(df_fc_qp['ds'] >= six_months_ago) & (df_fc_qp['ds'] <= six_months_later)]
            filtered_data = pd.read_json(filter_data, orient='split')
            # Convert the 'ds' column to a datetime object if it's not already

            # Filter the DataFrame for this date range

            # Assuming filtered_data is another DataFrame you want to merge with
            # Merge the filtered DataFrame with filtered_data
            df_fc_qp_filtered = df_fc_qp_filtered.merge(filtered_data, on=['sku', 'warehouse_code', 'region'], how='inner')

            # Decide which set of columns to aggregate based on the value of quantity_sales_radio
            if quantity_sales_radio == 'quantity':
                agg_columns = ['quantity', 'q_upper', 'q_lower', 'q_trend', 'q_weekly', 'q_yearly']
            elif quantity_sales_radio == 'revenue':
                agg_columns = ['revenue', 'r_upper', 'r_lower', 'r_trend', 'r_weekly', 'r_yearly']
            else:
                raise ValueError("quantity_sales_radio must be either 'quantity' or 'revenue'")

            # Create aggregation dictionary
            agg_dict = {col: 'sum' for col in agg_columns}
            #keep only ds and agg_columns
            columns=['ds']+agg_columns
            # Group by the specified columns and aggregate
            df_ds = df_fc_qp_filtered[columns].groupby([
                pd.Grouper(freq=sample_rate_dict[time_window], key='ds')
            ]).agg(agg_dict).reset_index()


            # Inside your update_demand_forecast_graph function, after you define df_ds and set 'date' as its index:


            today = datetime.now()

            df_ds['ds'] = pd.to_datetime(df_ds['ds'], errors='coerce')


            # Create subplots: use 'domain' type for Pie subplot
            fig_components = make_subplots(rows=2, cols=1)
            fig_components.update_layout(title_text = "Forecasting Model Components")
            # Add traces
            fig_components.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[3]], name='Trend'), row=1, col=1)

            if sample_rate_dict[time_window] == 'D':
                fig_components.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[4]], name='Weekly'), row=2, col=1)
            fig_components.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[5]], name='Yearly'), row=2, col=1)

            # Update layout
            fig_components.update_xaxes(title_text="Date", row=1, col=1)
            fig_components.update_yaxes(title_text="Trend Value", row=1, col=1)

            fig_components.update_xaxes(title_text="Date", row=2, col=1)
            fig_components.update_yaxes(title_text="Seasonality Value", row=2, col=1)
            # Add this figure to your Dash application

            # Adjust forecasted data and confidence intervals to be no lower than 0
            df_ds[agg_columns[0]] = np.maximum(0, df_ds[agg_columns[0]])
            df_ds[agg_columns[1]] = np.maximum(0, df_ds[agg_columns[1]])
            df_ds[agg_columns[2]] = np.maximum(0, df_ds[agg_columns[2]])

            # Create a Dash figure with Plotly
            fig = go.Figure()

            # Add actual data to the figure
            fig.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[0]], name='Actual'))
            # Add the forecasted data to the figure
            fig.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[0]], name='Forecast'))
            # Add the forecast components to the figure
            fig.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[1]], name='Lower Bound of Forecast', line=dict(width=0)))
            fig.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds[agg_columns[2]], name='Upper Bound of Forecast', fill='tonexty'))
            fig.update_layout(title=f'RDX Demand Forecast for {quantity_sales_radio}',
                              xaxis_title='Date', yaxis_title=quantity_sales_radio, height=400)
        return html.Div([
            dcc.Graph(id='forecast-data-graph', figure=fig),
            html.Hr(),
            dcc.Graph(id='components-data-graph', figure=fig_components),
        ])
    else:
        download_columns=['sku','region','warehouse_code','ds','quantity','revenue']
        forecast_table=dash_table.DataTable(
            id='forecast-table',
            columns=[{"name": i, "id": i} for i in download_columns],
            data=df_fc_qp[download_columns].head(100).to_dict('records'),
            page_size=24,
            sort_action="native",
            sort_mode="multi",
            style_cell_conditional=[
                {
                    'if': {'column_id': c},
                    'textAlign': 'left'
                } for c in ['Date', 'Region']
            ])

        return html.Div([ # Forecast Data Table
        html.Div([forecast_table],className="col-md-12"),
        html.A('Download CSV', id='download-button', className='btn btn-primary', download="forecast_data.csv", href="",
               target="_blank"),
        ],className="col-md-12")


@app.callback(
    Output('download-button', 'href'),
    Input('forecast-table', 'data'))
def update_download_link(data):
    df_to_download = pd.DataFrame.from_records(data)
    csv_string = df_to_download.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string
