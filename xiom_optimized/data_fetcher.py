import pandas as pd
from common.local_constants import region_warehouse_codes
from common.logger_ import get_logger
from xiom_optimized.cache_manager import CacheManager

logger = get_logger()
logger.info("Xdemand app starting")

# Instantiate CacheManager
cache_manager = CacheManager()

def fetch_ph_data():
    ph_data = pd.read_json(cache_manager.query_ph_data(), orient='split')
    ph_data['sku'] = ph_data.im_sku
    ph_data.fillna('', inplace=True)
    return ph_data

def fetch_daily_sales():
    df_daily_sales_da = pd.read_json(cache_manager.query_df_daily_sales(), convert_dates=['date'], orient='split')
    df_sales = pd.read_json(cache_manager.query_df_daily_sales(), convert_dates=['date'], orient='split')
    df_sales.columns = df_sales.columns.str.lower()
    df_sales['date'] = pd.to_datetime(df_sales['date'])
    return df_daily_sales_da, df_sales

def fetch_fc_qp():
    df_fc_qp = pd.read_json(cache_manager.query_df_fc_qp(), convert_dates=['ds'], orient='split')
    df_fc_qp['warehouse_code'] = df_fc_qp['region'].map(region_warehouse_codes)
    return df_fc_qp

def fetch_price_recommendations():
    df_price_rec = pd.read_json(cache_manager.query_price_recommender(), convert_dates=['ds'], orient='split')
    df_price_rec_summary = pd.read_json(cache_manager.query_price_recommender_summary(), convert_dates=['ds'], orient='split')
    return df_price_rec, df_price_rec_summary

def fetch_price_reference():
    df_price_reference = pd.read_json(cache_manager.query_price_reference(), convert_dates=['date'], orient='split')
    df_price_reference['warehouse_code'] = df_price_reference['region'].map(region_warehouse_codes)
    df_price_reference = df_price_reference.drop(columns=['region', 'date'])
    df_price_reference = df_price_reference.groupby(['sku', 'warehouse_code'])['price'].mean().reset_index()
    return df_price_reference

def fetch_price_sensing():
    return pd.read_json(cache_manager.query_price_sensing_tab(), convert_dates=['date'], orient='split')

def fetch_price_regression():
    return pd.read_json(cache_manager.query_price_regression_tab(), convert_dates=['date'], orient='split')

def fetch_sku_summary(df_daily_sales_da):
    return df_daily_sales_da.groupby(['sku'])[['quantity', 'revenue']].sum().reset_index()

def fetch_stockout_past():
    return pd.read_json(cache_manager.query_stockout_past(), convert_dates=['date'], orient='split')

def fetch_running_stock(df_price_reference):
    df_running_stock = pd.read_json(cache_manager.query_df_running_stock(), convert_dates=['date'], orient='split')
    df_running_stock['ds'] = pd.to_datetime(df_running_stock['ds'])
    df_running_stock = pd.merge(df_running_stock, df_price_reference[['sku', 'warehouse_code', 'price']], how='left', on=['sku', 'warehouse_code'])
    return df_running_stock

def fetch_aggregated_data(df_daily_sales_da, df_sales):
    df_agg_daily_3months = df_daily_sales_da.groupby(['sku', 'region', 'date'])[['quantity', 'revenue']].sum().reset_index()
    df_daily_sales_da['warehouse_code'] = df_daily_sales_da['region'].map(region_warehouse_codes)
    df_agg_monthly_3years = df_sales.groupby(['sku', 'warehouse_code', pd.Grouper(key='date', freq='M')])[['quantity', 'revenue']].sum().reset_index()
    return df_agg_daily_3months, df_agg_monthly_3years

# fetch product hierarchy data
ph_data = fetch_ph_data()

# fetch daily sales data
df_daily_sales_da, df_sales = fetch_daily_sales()

# fetch forecast quantity and price data
df_fc_qp = fetch_fc_qp()

# fetch price recommendations
df_price_rec, df_price_rec_summary = fetch_price_recommendations()

# fetch price reference, price sensing and price regression data
df_price_reference = fetch_price_reference()

# fetch price sensing and price regression data
df_price_sensing_tab = fetch_price_sensing()

# fetch price regression data
df_price_regression_tab = fetch_price_regression()

# fetch sku summary, stockout past and running stock data
df_sku_sum = fetch_sku_summary(df_daily_sales_da)

# fetch stockout past data
df_stockout_past = fetch_stockout_past()

# fetch running stock data
df_running_stock = fetch_running_stock(df_price_reference)

# fetch aggregated data
df_agg_daily_3months, df_agg_monthly_3years = fetch_aggregated_data(df_daily_sales_da, df_sales)

