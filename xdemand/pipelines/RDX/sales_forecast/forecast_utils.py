import holidays
import pandas as pd
from prophet import Prophet
from sqlalchemy import text
import logging

from common.db_connection import engine
from common.local_constants import region_warehouse_codes
from config import forecast_settings as cf
periods = cf.forecast_periods
freq = cf.forecast_period_freq

logger = logging.getLogger(__name__)


def forecast_sku(sku_data, sku, target_variable, region):
    # Preprocess the data
    df = sku_data[['date_part', target_variable]]
    prophet_data = df.rename(columns={'date_part': 'ds', target_variable: 'y'})
    logger.info(f"""Forecasting SKU {sku} for {target_variable} in {region} for next \
                {periods} days with {len(prophet_data)} rows""")
    # Instantiate the Prophet model
    model = Prophet(growth='linear', yearly_seasonality=True,
                    weekly_seasonality=True,
                    seasonality_mode='multiplicative')
    model.add_country_holidays(country_name=region)
    try:
        # Fit the model to the data
        model.fit(prophet_data)
        # Create a dataframe for future dates
        future = model.make_future_dataframe(periods=periods, freq=freq)
        # Forecast the future sales
        forecast = model.predict(future)
        # Filter the forecast to the next 3 months only
        forecast = forecast.tail(cf.forecast_tail_periods)
        # Add the SKU to the forecast dataframe
        forecast = forecast[
            ['ds', 'trend', 'yhat', 'yhat_lower', 'yhat_upper', 'trend_lower', 'trend_upper', 'weekly', 'yearly']]
        forecast['sku'] = sku
        forecast['region'] = region

    except:
        return
    return forecast


def prophet_pipeline_daily_sales_transform(sales_df):
    sales_df['date'] = pd.to_datetime(sales_df['date'])
    sales_df['date_part'] = pd.to_datetime(sales_df['date'].dt.date)
    # Convert all columns to lowercase
    sales_df.columns = sales_df.columns.str.lower()

    rows_per_sku = sales_df.groupby(['region', 'sku'])['date_part'].count().reset_index()
    rows_per_sku.describe()

    rows_per_sku = rows_per_sku[rows_per_sku['date_part'] > cf.min_rows_per_sku]
    sales_df = pd.merge(sales_df, rows_per_sku[['region', 'sku']], how='inner', on=['region', 'sku'])

    # Group by 'sku' and sum the 'quantity'
    grouped = sales_df.groupby('sku')['revenue'].sum()
    # Sort the summed quantities in descending order and take the top 100
    top_products = grouped.sort_values(ascending=False).head(cf.top_n)

    # Filter the original DataFrame for only the top 100 SKUs
    sales_df = sales_df[sales_df['sku'].isin(top_products.index)]
    return sales_df


def forecast_sales(grouper, target_variable, max_date):
    # Initialize an empty dataframe to store the forecasts
    all_forecasts = pd.DataFrame()
    # Loop through each SKU and forecast the sales
    for (region, sku), group in grouper:
        sku_data = group
        if region == 'USA':
            forecast = forecast_sku(sku_data, sku, target_variable, region="US")
        else:
            forecast = forecast_sku(sku_data, sku, target_variable, region)
        if forecast is not None:
            forecast['sku'] = sku
            forecast['region'] = 'US' if region == 'USA' else region
            forecast['warehouse_code'] = forecast['region'].replace(region_warehouse_codes)
            all_forecasts = pd.concat([all_forecasts, forecast], axis=0, ignore_index=True)
        else:
            print("No forecast for this SKU" + sku + "in region" + region)

    all_forecasts['yhat'] = all_forecasts['yhat'].clip(lower=0)
    all_forecasts['last_data_seen'] = max_date
    print(str(max(all_forecasts['ds'])) + "Max Date for Forecast in the data")
    return all_forecasts


def add_holidays(quantity_forecasts, max_date):
    # add holidays to the forecast
    for region in quantity_forecasts['region'].unique():
        current_year = max_date.year
        country_holidays = holidays.country_holidays(country=region, years=range(current_year - 1, current_year + 2))
        country_holidays_df = pd.DataFrame.from_dict(country_holidays, orient='index', columns=['holiday'])
        country_holidays_df['ds'] = pd.to_datetime(country_holidays_df.index)
        country_holidays_df['region'] = 'US' if region == 'USA' else region
        quantity_forecasts['region'] = quantity_forecasts['region']
    return pd.merge(quantity_forecasts, country_holidays_df, how='left', on=['ds', 'region'])
