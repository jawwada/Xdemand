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

import warnings
warnings.filterwarnings("ignore")

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
        query = ("""SELECT lph.im_sku as sku,lph.channel, lph.region, 
                    lph.level_1, lph.level_2, lph.level_3, lph.level_4
                    FROM look_product_hierarchy lph
                 """)
        df = pd.read_sql_query(query, cnxn)
        df['warehouse_code']=df['region'].map(region_warehouse_codes)

        query_2 = ("""SELECT sku, warehouse_code from stat_forecast_data_quantity""")
        df_2 = pd.read_sql_query(query_2, cnxn)
        df = df.merge(df_2, on=['sku','warehouse_code'], how='inner')
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_daily_sales_oos(self,ph_data):
        query = """
        SELECT * FROM agg_im_sku_daily_sales_oos
        Where date > DATEADD(year, -3, GETDATE()) 
        ORDER BY sku, warehouse_code, region, date;
        """
        with cnxn.connect() as con:
            daily_sales = pd.read_sql_query(query, con)
        daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
        daily_sales['year'] = daily_sales['date'].dt.year
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
        daily_sales['revenue'] = daily_sales['revenue'].astype(float)
        daily_sales = daily_sales.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')
        return daily_sales.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_daily_sales_forecast_skus(self, ph_data):
        query = """SELECT agg.*
            FROM agg_im_sku_daily_sales agg
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity
            ) stat ON agg.sku = stat.sku AND agg.warehouse_code = stat.warehouse_code
            WHERE agg.date > DATEADD(year, -3, GETDATE()) 
            ORDER BY agg.sku, agg.region, agg.date; 
            """
        with cnxn.connect() as con:
            daily_sales = pd.read_sql_query(query, con)
        daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
        daily_sales['year'] = daily_sales['date'].dt.year
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
        daily_sales['revenue'] = daily_sales['revenue'].astype(float)
        daily_sales = daily_sales.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')
        return daily_sales.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_daily_sales(self, ph_data):
        query = """
        SELECT agg.* FROM agg_im_sku_daily_sales agg
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = agg.sku AND fcst.warehouse_code = agg.warehouse_code
        where date > DATEADD(year, -3, GETDATE()) 
        ORDER BY agg.sku, agg.region, agg.date;
        """
        df = pd.read_sql_query(query, cnxn)
        df['date'] = pd.to_datetime(df['date'])
        df['warehouse_code'] = df['region'].map(region_warehouse_codes)
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_fc_qp(self, ph_data):
        query = f"""SELECT stat.*
                    FROM stat_forecast_quantity_revenue stat
                    WHERE ds >= DATEADD(day, -350, GETDATE()) 
                    ORDER BY sku, warehouse_code, ds"""
        df = pd.read_sql_query(query, cnxn)
        df['ds'] = pd.to_datetime(df['ds'])
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')

        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_df_running_stock(self,ph_data):
        query = """
        select stat.* from stat_running_stock_forecast stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
            WHERE ds >= CAST(GETDATE() AS DATE)
            """
        df = pd.read_sql_query(query, cnxn)
        df.date = pd.to_datetime(df.ds).dt.date
        df['ds'] = pd.to_datetime(df['ds'])
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_stockout_past(self, ph_data):
        query = """SELECT stat.* FROM stat_stock_out_past stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code"""
        df = pd.read_sql_query(query, cnxn)
        df.date = pd.to_datetime(df.date)
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')

        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_sensing_tab(self,ph_data):
        query = """SELECT stat.* FROM stat_regression_coeff_price_quantity stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
                  order by price_elasticity desc"""
        df = pd.read_sql_query(query, cnxn)
        df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')

        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_regression_tab(self,ph_data):
        query = """SELECT stat.* FROM  stat_regression_price_quantity stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code 
                FROM stat_forecast_data_quantity 
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code"""
        df = pd.read_sql_query(query, cnxn)
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')

        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_reference(self, ph_data):
        query = f"""SELECT stat.sku, stat.warehouse_code,stat.price 
        FROM look_latest_price_reference stat
             where date > DATEADD(year, -1, GETDATE()) 
             order by stat.sku, warehouse_code"""
        df = pd.read_sql_query(query, cnxn)
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')
        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_recommender_summary(self, ph_data):
        query = """
            SELECT
              stat.[sku],
              stat.[warehouse_code],
              stat.[ref_price],
              stat.[mean_demand],
              stat.[current_stock],
              stat.[understock_days],
              stat.[overstock_days],
              stat.[price_elasticity],
              stat.[revenue_before],
              stat.[revenue_after],
              stat.[price_new],
              stat.[price_old],
              stat.[opt_stock_level]
            FROM [dbo].[stat_price_recommender_summary] stat
            JOIN (
                SELECT DISTINCT sku, warehouse_code
                FROM stat_forecast_data_quantity
            ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
            """
        df = pd.read_sql_query(query, cnxn)
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')

        return df.to_json(date_format='iso', orient='split')

    @cache_decorator
    def query_price_recommender(self, ph_data):
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
        df = pd.read_sql_query(query, cnxn)
        df['ds'] = pd.to_datetime(df['ds'])
        df = df.merge(ph_data[['sku','level_1']].drop_duplicates(), on='sku', how='inner')

        return df.to_json(date_format='iso', orient='split')