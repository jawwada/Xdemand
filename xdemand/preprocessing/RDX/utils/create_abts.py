import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from xdemand.preprocessing.RDX.utils.sales_aggregate import get_agg_sales
from xdemand.preprocessing.RDX.utils.feature_utils import get_weather_data, get_temporal_lag_features, get_temporal_features
from joblib import Memory
from common.logger_ import get_logger
import numpy as np
# Create a memory object with a specific cache directory.
memory = Memory("cache_directory", verbose=0)


@memory.cache
def create_sales_abt(lag_periods,weather_cols,countries,
                     weather_country, weather_city,
                     date_from, agg_table='sales',
                     sales_freq='D', lag_freq=None, lag_columns=None,channel=None,region='UK'):

    logger = get_logger()
    logger.info(f"Parameter for ABT  {lag_periods} lag periods, {weather_cols} weather columns, "
                f" {countries} countries, {weather_country} weather country, {weather_city} weather city, "
                f" {date_from} date from, {agg_table} agg table, {sales_freq} sales freq, {lag_freq} lag freq,"
                f" {lag_columns} lag columns")

    if agg_table=='sales':
        df_dsa=get_agg_sales(channel=channel,region=region,date_from=date_from,freq=sales_freq)
    logger.info(f"Created df_dsa , {df_dsa.shape[0]} rows and {df_dsa.shape[1]} columns")
    logger.info(f"Created df_dsa , {df_dsa['date'].max()} max date and {df_dsa['date'].min()} min date")
    df_dsa_abt = get_temporal_features(df_dsa, lag_columns, lag_freq, lag_periods, countries)
    logger.info(f"Created ABT with temporal features, {df_dsa_abt.shape[0]} rows and {df_dsa_abt.shape[1]} columns")
    if lag_columns is not None:
        df_dsa_abt = get_temporal_lag_features(df_dsa_abt.copy(deep=True),lag_columns,lag_freq,lag_periods,countries)
        logger.info(f"Created ABT with temporal log features, {df_dsa_abt.shape[0]} rows and {df_dsa_abt.shape[1]} columns")
        df_dsa_abt['temp_date'] = df_dsa_abt['date'].dt.date.copy()
    if weather_cols is not None:
        df_dsa_abt = merge_weather_data(df_dsa_abt,weather_cols,weather_country,weather_city)
    df_dsa_abt.sort_values(by=['sku', 'date'], inplace=True)

    df_dsa_abt['promotional rebates'] = df_dsa_abt['promotional rebates'].fillna(0)
    df_dsa_abt['percent_change'] = df_dsa_abt['promotional rebates'] / (df_dsa_abt['revenue'] + df_dsa_abt['promotional rebates']) * 100
    df_dsa_abt['percent_change'] = df_dsa_abt['percent_change'].fillna(0)
    df_dsa_abt['percent_change'] = df_dsa_abt['percent_change'].replace(np.inf, 0)

    return df_dsa_abt


def merge_weather_data(df_dsa_abt, weather_cols, weather_country, weather_city):
    logger = get_logger()
    weather_data = get_weather_data(weather_cols,weather_country,weather_city)
    logger.info(f"Weather Data , {weather_data['date'].max()} max date and {weather_data['date'].min()} min date")
    weather_data['temp_date'] = weather_data['date'].dt.date.copy()

    df_dsa_abt_w = df_dsa_abt.merge(weather_data, on='temp_date')
    df_dsa_abt_w.drop(['date_y', 'temp_date'], axis=1, inplace=True)
    df_dsa_abt_w.rename(columns={'date_x': 'date'}, inplace=True)
    logger.info(f"Created ABT with weather features, {df_dsa_abt_w.shape[0]} rows and {df_dsa_abt_w.shape[1]} columns")

    return df_dsa_abt_w
