from functools import wraps
from pathlib import Path

import pandas as pd
from flask_caching import Cache

from common.local_constants import region_warehouse_codes
from common.logger_ import get_logger
from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.config_constants import CACHE_DIR
from xiom_optimized.utils.config_constants import CACHE_REDIS_URL
from xiom_optimized.utils.config_constants import CACHE_TYPE
from xiom_optimized.utils.config_constants import TIMEOUT
from common.db_connection import engine
import warnings
warnings.filterwarnings("ignore")
logger = get_logger()
logger.info("Xdemand app starting")


# define CacheDecorator class
class CacheDecoratorFlask:
    def __init__(self):
        if CACHE_TYPE == 'redis':
            self.cache = Cache(app.server, config={
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': CACHE_REDIS_URL,
                'CACHE_DEFAULT_TIMEOUT': TIMEOUT
            })
        elif CACHE_TYPE == 'filesystem':
            self.cache = Cache(app.server, config={
                'CACHE_TYPE': 'filesystem',
                'CACHE_DIR': CACHE_DIR,
                'CACHE_DEFAULT_TIMEOUT': TIMEOUT
            })
            Path(CACHE_DIR).mkdir(exist_ok=True)
        else:
            raise ValueError(f'CACHE_TYPE {CACHE_TYPE} not supported')

    def cache_decorator(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.cache.memoize(timeout=TIMEOUT)(func)(*args, **kwargs)

        return wrapper

global cache_decorator

class CacheManager():

    @cache_decorator
    def query_ph_data(self):
        query = "SELECT * FROM look_product_hierarchy where im_sku in (select distinct sku from stat_forecast_data_quantity)"
        df = pd.read_sql_query(query, engine)
        df['sku'] = df.im_sku
        df['warehouse_code'] = df['region'].map(region_warehouse_codes)
        return df

    @cache_decorator
    def query_df_daily_sales_oos(self):
        query = """
        SELECT * FROM agg_im_sku_daily_sales_oos
        WHERE sku IN (SELECT DISTINCT sku FROM stat_forecast_data_quantity) 
        AND date > DATEADD(year, -3, GETDATE()) 
        ORDER BY sku, region, date;
        """
        with engine.connect() as con:
            daily_sales = pd.read_sql_query(query, con)
        daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
        daily_sales['year'] = daily_sales['date'].dt.year
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
        daily_sales['revenue'] = daily_sales['revenue'].astype(float)
        return daily_sales

    @cache_decorator
    def query_df_daily_sales_forecast_skus(self):
        query = """SELECT agg.*
            FROM agg_im_sku_daily_sales agg
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity
            ) stat ON agg.sku = stat.sku AND agg.warehouse_code = stat.warehouse_code
            WHERE agg.date > DATEADD(year, -3, GETDATE()) 
            ORDER BY agg.sku, agg.region, agg.date; 
            """
        with engine.connect() as con:
            daily_sales = pd.read_sql_query(query, con)
        daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
        daily_sales['year'] = daily_sales['date'].dt.year
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
        daily_sales['revenue'] = daily_sales['revenue'].astype(float)
        return daily_sales

    @cache_decorator
    def query_df_daily_sales(self):
        query = """
        SELECT * FROM agg_im_sku_daily_sales 
        WHERE sku IN (SELECT DISTINCT sku FROM look_product_hierarchy) 
        AND date > DATEADD(year, -3, GETDATE()) 
        ORDER BY sku, region, date;
        """
        with engine.connect() as con:
            daily_sales = pd.read_sql_query(query, con)
        daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
        daily_sales['year'] = daily_sales['date'].dt.year
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
        daily_sales['revenue'] = daily_sales['revenue'].astype(float)
        return daily_sales

    @cache_decorator
    def query_df_fc_qp(self):
        query = f"""SELECT * FROM stat_forecast_quantity_revenue
                WHERE ds > DATEADD(year, -3, GETDATE()) ORDER BY ds, sku, warehouse_code;"""
        df = pd.read_sql_query(query, engine)
        df['ds'] = pd.to_datetime(df['ds'])
        return df

    @cache_decorator
    def query_df_running_stock(self):
        query = """
        select * from stat_running_stock_forecast stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
        """
        df = pd.read_sql_query(query, engine)
        df.date = pd.to_datetime(df.ds).dt.date
        df['ds'] = pd.to_datetime(df['ds'])
        return df

    @cache_decorator
    def query_stockout_past(self):
        query = """SELECT * FROM stat_stock_out_past stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code"""
        df = pd.read_sql_query(query, engine)
        df.date = pd.to_datetime(df.date)
        return df

    @cache_decorator
    def query_price_sensing_tab(self):
        query = """SELECT * FROM stat_regression_coeff_avg_price_quantity stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
                  order by price_elasticity desc"""
        df = pd.read_sql_query(query, engine)
        df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
        return df

    @cache_decorator
    def query_price_regression_tab(self):
        query = """SELECT * FROM  stat_regression_avg_price_quantity stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code"""
        df = pd.read_sql_query(query, engine)
        return df

    @cache_decorator
    def query_price_reference(self):
        query = f"""SELECT stat.sku, stat.region,stat.price , stat.date
        FROM look_latest_price_reference stat
            JOIN (
                SELECT DISTINCT sku
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku 
             and date > DATEADD(year, -1, GETDATE()) order by stat.sku, region, date;"""
        df = pd.read_sql_query(query, engine)
        df['date'] = pd.to_datetime(df['date'])
        return df

    @cache_decorator
    def query_price_recommender_summary(self):
        query = f"""SELECT
          stat.[sku],
          mean_demand as yhat
          ,stat.[warehouse_code]
          ,[price_elasticity]
          ,[opt_stock_level]
          ,[revenue_before]
          ,[revenue_after]
          ,[price_new]
          ,[price_old]
            FROM [dbo].[stat_price_recommender_summary]
            stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
            """
        df = pd.read_sql_query(query, engine)
        return df

    @cache_decorator
    def query_price_recommender(self):
        query = f"""SELECT
        stat.[sku]
        , [ds]
        , stat.[warehouse_code]
        , [InTransit_Quantity]
        , [running_stock_after_forecast_adj] as running_stock_after_forecast_adj
        , [q_prime_adj] as q_prime_adj
        FROM[dbo].[stat_price_recommender] 
        stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
        """
        df = pd.read_sql_query(query, engine)
        df['ds'] = pd.to_datetime(df['ds'])
        return df