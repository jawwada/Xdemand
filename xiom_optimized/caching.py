from pathlib import Path

import pandas as pd
from flask_caching import Cache
from xiom_optimized.app_config_initial import app
from xiom_optimized.config_constants import CACHE_REDIS_URL, TIMEOUT, CACHE_TYPE, CACHE_DIR, cnxn
from common.logger_ import get_logger
from common.local_constants import region_warehouse_codes


logger = get_logger()
logger.info("Xdemand app starting")

if CACHE_TYPE == 'redis':
    cached_funcs = []
    cache = Cache(app.server, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': CACHE_REDIS_URL,  # Read the connection string from an environment variable
        'CACHE_DEFAULT_TIMEOUT': TIMEOUT
    })

elif CACHE_TYPE == 'filesystem':
    cache=Cache(app.server, config={
        'CACHE_TYPE': 'filesystem',
        'CACHE_DIR': CACHE_DIR,
        'CACHE_DEFAULT_TIMEOUT': TIMEOUT
    })
    # local caching
    Path(CACHE_DIR).mkdir(exist_ok=True)
else:
    raise ValueError(f'CACHE_TYPE {CACHE_TYPE} not supported')


@cache.memoize(timeout=TIMEOUT)
def query_ph_data():
    query = "SELECT * FROM look_product_hierarchy where im_sku in (select distinct sku from stat_forecast_data_quantity)"
    df = pd.read_sql_query(query, cnxn)
    df['sku'] = df.im_sku
    df['warehouse_code'] = df['region'].map(region_warehouse_codes)

    return df.to_json(date_format='iso', orient='split')

ph_data = pd.read_json(query_ph_data(), orient='split')
ph_data['sku'] = ph_data.im_sku
ph_data.fillna('', inplace=True)

@cache.memoize(timeout=TIMEOUT)
def query_df_weekly_sales():
    query = f"""SELECT * FROM agg_im_sku_weekly_sales 
    where sku in (select distinct sku from stat_forecast_data_quantity) and date > DATEADD(year, -3, GETDATE()) order by sku, region, date;"""
    df = pd.read_sql_query(query, cnxn)
    df['date'] = pd.to_datetime(df['date'])
    df['warehouse_code'] = df['region'].map(region_warehouse_codes)
    #perform weekly aggregation with W-MON as the start of the week
    return df.to_json(date_format='iso', orient='split')

@cache.memoize(timeout=TIMEOUT)
def query_df_daily_sales():
    query = f"""SELECT * FROM agg_im_sku_daily_sales 
    where sku in (select distinct sku from stat_forecast_data_quantity) and date > DATEADD(year, -3, GETDATE()) order by sku, region, date;"""

    df = pd.read_sql_query(query, cnxn)
    df['date'] = pd.to_datetime(df['date'])
    #perform weekly aggregation with W-MON as the start of the week
    df['warehouse_code'] = df['region'].map(region_warehouse_codes)
    return df.to_json(date_format='iso', orient='split')

@cache.memoize(timeout=TIMEOUT)
def query_df_fc_qp():
    query = f"""SELECT * FROM stat_forecast_quantity_revenue 
            WHERE sku IN (SELECT DISTINCT sku FROM stat_forecast_data_quantity) and ds > DATEADD(year, -1, GETDATE()) ORDER BY ds, sku, warehouse_code;"""
    df = pd.read_sql_query(query, cnxn)
    df['ds'] = pd.to_datetime(df['ds'])
    return df.to_json(date_format='iso', orient='split')


@cache.memoize(timeout=TIMEOUT)
def query_df_running_stock():
    query = """
    select * from stat_running_stock_forecast 
    WHERE ds >= CAST(GETDATE() AS DATE) 
    AND sku in (SELECT DISTINCT sku FROM stat_forecast_data_quantity);
    """
    df = pd.read_sql_query(query, cnxn)
    df.date = pd.to_datetime(df.ds).dt.date
    df['ds'] = pd.to_datetime(df['ds'])
    #df['sku'] = df.im_sku
    return df.to_json(date_format='iso', orient='split')


@cache.memoize(timeout=TIMEOUT)
def query_stockout_past():
    query = "SELECT * FROM stat_stock_out_past where sku in (select distinct sku from stat_forecast_data_quantity)"
    df = pd.read_sql_query(query, cnxn)
    df.date = pd.to_datetime(df.date)

    return df.to_json(date_format='iso', orient='split')

@cache.memoize(timeout=TIMEOUT)
def query_price_sensing_tab():
    query = ("SELECT * FROM stat_regression_coeff_avg_price_quantity where"
             " sku in (select distinct sku from stat_forecast_data_quantity) order by price_elasticity desc")
    df = pd.read_sql_query(query, cnxn)
    df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
    print(df.head())
    return df.to_json(date_format='iso', orient='split')
def query_price_regression_tab():
    query = "SELECT * FROM  stat_regression_avg_price_quantity where sku in (select distinct sku from stat_forecast_data_quantity)"
    df = pd.read_sql_query(query, cnxn)

    return df.to_json(date_format='iso', orient='split')

@cache.memoize(timeout=TIMEOUT)
def query_price_reference():
    query = f"""SELECT * FROM look_latest_price_reference 
    where sku in (select distinct sku from stat_forecast_data_quantity) and date > DATEADD(year, -1, GETDATE()) order by sku, region, date;"""

    df = pd.read_sql_query(query, cnxn)
    df['date'] = pd.to_datetime(df['date'])
    #perform weekly aggregation with W-MON as the start of the week

    return df.to_json(date_format='iso', orient='split')
@cache.memoize(timeout=TIMEOUT)
def query_price_recommender_summary():
    query = f"""SELECT 
      [sku],
      mean_demand as yhat
      ,[warehouse_code]
      ,[price_elasticity]
      ,[opt_stock_level]
      ,[revenue_before]
      ,[revenue_after]
      ,[price_new]
      ,[price_old]
        FROM [dbo].[stat_price_recommender_summary]"""

    df = pd.read_sql_query(query, cnxn)
    #perform weekly aggregation with W-MON as the start of the week

    return df.to_json(date_format='iso', orient='split')

@cache.memoize(timeout=TIMEOUT)
def query_price_recommender():
    query = f"""SELECT
    [sku]
    , [ds]
    , [warehouse_code]
    , [InTransit_Quantity]
    , [running_stock_after_forecast_adj] as running_stock_after_forecast_adj
    , [q_prime_adj] as q_prime_adj 
    FROM[dbo].[stat_price_recommender]"""
    df = pd.read_sql_query(query, cnxn)
    df['ds'] = pd.to_datetime(df['ds'])
    #perform weekly aggregation with W-MON as the start of the week

    return df.to_json(date_format='iso', orient='split')

# Prepare df_daily_sales_da
df_daily_sales_da =  pd.read_json(query_df_daily_sales(), convert_dates=['date'], orient='split')


# Prepare df_sales
df_sales = pd.read_json(query_df_daily_sales(), convert_dates=['date'], orient='split')
df_sales.columns=df_sales.columns.str.lower()
# Prepare df_daily_sales_da
df_sales['date'] = pd.to_datetime(df_sales['date'])



# Prepare df_fc_qp
df_fc_qp = pd.read_json(query_df_fc_qp(), convert_dates=['ds'], orient='split')
#df_fc_qp['price']=df_fc_qp['revenue']/df_fc_qp['quantity']
df_fc_qp['warehouse_code'] = df_fc_qp['region'].map(region_warehouse_codes)
#drop the region column


# Prepare Price Sensing, Price Regression, and Price Reference
df_price_rec=pd.DataFrame()
df_price_rec_summary=pd.DataFrame()
df_price_rec=pd.read_json(query_price_recommender(), convert_dates=['ds'], orient='split')
df_price_rec_summary=pd.read_json(query_price_recommender_summary(), convert_dates=['ds'], orient='split')

df_price_reference = pd.read_json(query_price_reference(), convert_dates=['date'], orient='split')
df_price_reference['warehouse_code'] = df_price_reference['region'].map(region_warehouse_codes)
df_price_reference = df_price_reference.drop(columns=['region'])

df_price_sensing_tab = pd.read_json(query_price_sensing_tab(), convert_dates=['date'], orient='split')
df_price_regression_tab = pd.read_json(query_price_regression_tab(), convert_dates=['date'], orient='split')

# Prepare product tree map
df_sku_sum=df_daily_sales_da.groupby(['sku'])[['quantity','revenue']].sum().reset_index()

# Prepare stockout past
df_stockout_past= pd.read_json(query_stockout_past(), convert_dates=['date'], orient='split')

# Prepare running stock
df_running_stock = pd.read_json(query_df_running_stock(), convert_dates=['date'], orient='split')
df_running_stock['ds']=pd.to_datetime(df_running_stock['ds'])

# merge the two dataframes
df_running_stock = pd.merge(df_running_stock, df_price_reference[['sku','warehouse_code','price']], how='left', on=['sku','warehouse_code'])

df_agg_daily_3months= df_daily_sales_da.groupby(['sku', 'region', 'date'])[['quantity','revenue']].sum().reset_index()
# transform the daily sales data to monthly and change region to warehouse_code
df_daily_sales_da['warehouse_code'] = df_daily_sales_da['region'].map(region_warehouse_codes)
df_agg_monthly_3years = df_sales.groupby(['sku', 'warehouse_code', pd.Grouper(key='date', freq='M')])[['quantity','revenue']].sum().reset_index()
