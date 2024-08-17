from functools import wraps
from pathlib import Path

import pandas as pd
from flask_caching import Cache

from common.local_constants import region_warehouse_codes
from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.config_constants import CACHE_DIR
from xiom_optimized.utils.config_constants import CACHE_REDIS_URL
from xiom_optimized.utils.config_constants import CACHE_TYPE
from xiom_optimized.utils.config_constants import TIMEOUT
from xiom_optimized.utils.config_constants import cnxn

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("Xdemand app starting")


# define CacheDecorator class
class CacheDecorator:
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


cache_decorator = CacheDecorator().cache_decorator


class CacheManager:
    def __init__(self):
        pass

    @cache_decorator
    def query_ph_data(self):
        query = "SELECT * FROM look_product_hierarchy where im_sku in (select distinct sku from stat_forecast_data_quantity)"
        df = pd.read_sql_query(query, cnxn)
        df['sku'] = df.im_sku
        df['warehouse_code'] = df['region'].map(region_warehouse_codes)
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_daily_sales(self):
        query = f"""SELECT * FROM agg_im_sku_daily_sales
        where sku in (select distinct sku from stat_forecast_data_quantity) and date > DATEADD(year, -3, GETDATE()) order by sku, region, date;"""
        df = pd.read_sql_query(query, cnxn)
        df['date'] = pd.to_datetime(df['date'])
        df['warehouse_code'] = df['region'].map(region_warehouse_codes)
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_fc_qp(self):
        query = f"""SELECT * FROM stat_forecast_quantity_revenue
                WHERE sku IN (SELECT DISTINCT sku FROM stat_forecast_data_quantity) and ds > DATEADD(year, -1, GETDATE()) ORDER BY ds, sku, warehouse_code;"""
        df = pd.read_sql_query(query, cnxn)
        df['ds'] = pd.to_datetime(df['ds'])
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_running_stock(self):
        query = """
        select * from stat_running_stock_forecast
        WHERE ds >= CAST(GETDATE() AS DATE)
        AND sku in (SELECT DISTINCT sku FROM stat_forecast_data_quantity);
        """
        df = pd.read_sql_query(query, cnxn)
        df.date = pd.to_datetime(df.ds).dt.date
        df['ds'] = pd.to_datetime(df['ds'])
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_stockout_past(self):
        query = "SELECT * FROM stat_stock_out_past where sku in (select distinct sku from stat_forecast_data_quantity)"
        df = pd.read_sql_query(query, cnxn)
        df.date = pd.to_datetime(df.date)
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_sensing_tab(self):
        query = ("SELECT * FROM stat_regression_coeff_avg_price_quantity where"
                 " sku in (select distinct sku from stat_forecast_data_quantity) order by price_elasticity desc")
        df = pd.read_sql_query(query, cnxn)
        df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
        return df.to_json(date_format='iso', orient='split')

    def query_price_regression_tab(self):
        query = "SELECT * FROM  stat_regression_avg_price_quantity where sku in (select distinct sku from stat_forecast_data_quantity)"
        df = pd.read_sql_query(query, cnxn)
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_reference(self):
        query = f"""SELECT * FROM look_latest_price_reference
        where sku in (select distinct sku from stat_forecast_data_quantity) and date > DATEADD(year, -1, GETDATE()) order by sku, region, date;"""
        df = pd.read_sql_query(query, cnxn)
        df['date'] = pd.to_datetime(df['date'])
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_recommender_summary(self):
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
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_recommender(self):
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
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_ph_data(self):
        query = "SELECT * FROM look_product_hierarchy where im_sku in (select distinct sku from stat_forecast_data_quantity)"
        df = pd.read_sql_query(query, cnxn)
        df['sku'] = df.im_sku
        df['warehouse_code'] = df['region'].map(region_warehouse_codes)
        return df.to_json(date_format='iso', orient='split')
