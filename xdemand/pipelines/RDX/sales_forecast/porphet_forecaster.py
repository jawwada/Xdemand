import pandas as pd
from prophet import Prophet
import logging

from xdemand.pipelines.utils import filter_top_n

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ProphetForecaster:
    def __init__(self, periods, freq, forecast_tail_periods):
        self.periods = periods
        self.freq = freq
        self.forecast_tail_periods = forecast_tail_periods

    def forecast_sku(self, sku_data, sku, warehouse_code, target, seasonality_mode='additive'):
        # Preprocess the data
        df = sku_data[['date_part', target]]
        prophet_data = df.rename(columns={'date_part': 'ds', target: 'y'})
        logger.info(f"Forecasting SKU {sku} for {target} in {warehouse_code} for next {self.periods} days with {len(prophet_data)} rows")

        # Instantiate the Prophet model
        model = Prophet(growth='linear', yearly_seasonality=True,
                        weekly_seasonality=True,
                        seasonality_mode=seasonality_mode)
        model.add_country_holidays(country_name=warehouse_code)
        last_data_seen = prophet_data['ds'].max()
        try:
            # Fit the model to the data
            model.fit(prophet_data)
            # Create a dataframe for future dates
            future = model.make_future_dataframe(periods=self.periods, freq=self.freq)
            # Forecast the future sales
            forecast = model.predict(future)
            # Filter the forecast to the next forecast_tail_periods only
            forecast = forecast.tail(self.forecast_tail_periods)
            # Add the SKU to the forecast dataframe
            forecast['sku'] = sku
            forecast['warehouse_code'] = warehouse_code

            # select only the required columns, there are a lot holiday columns that are not needed
            forecast = forecast[[
                'ds', 'sku', 'warehouse_code', 'yhat',
                'yhat_lower', 'yhat_upper',
                'trend', 'weekly', 'yearly',
            ]]
            forecast['last_data_seen'] = last_data_seen

        except Exception as e:
            logger.error(f"Error in forecasting SKU {sku}: {e}")
            return None
        return forecast

    def prophet_daily_sales_transform(self, sales_df, min_rows_per_sku, top_n):
        sales_df['date_part'] = pd.to_datetime(sales_df['date'].dt.date)

        rows_per_sku = sales_df.groupby(['sku', 'warehouse_code'])['date_part'].count().reset_index()
        rows_per_sku = rows_per_sku[rows_per_sku['date_part'] > min_rows_per_sku]
        sales_df = pd.merge(sales_df, rows_per_sku[['sku', 'warehouse_code']], how='inner', on=['sku', 'warehouse_code'])
        sales_df = filter_top_n(sales_df, top_n)
        return sales_df

    def forecast_sales(self, grouper, max_date, target):
        # Initialize an empty dataframe to store the forecasts
        all_forecasts = pd.DataFrame()
        # Loop through each SKU and forecast the sales
        for (sku, warehouse_code), group in grouper:
            sku_data = group
            forecast = self.forecast_sku(sku_data, sku, warehouse_code, target)
            if forecast is not None:
                forecast['yhat'] = forecast['yhat'].clip(lower=0)
                forecast['last_data_seen'] = max_date
                all_forecasts = pd.concat([all_forecasts, forecast], axis=0, ignore_index=True)
            else:
                logger.warning(f"No forecast for SKU {sku} in warehouse_code {warehouse_code}")

        return all_forecasts