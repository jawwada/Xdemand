import os
import warnings
from functools import wraps

import pandas as pd
from joblib import Memory

from common.db_connection import engine
from common.local_constants import region_warehouse_codes
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

warnings.filterwarnings("ignore")

class CacheDecoratorJoblib:
    def __init__(self):
        cache_dir = os.path.join(os.getcwd(), 'cache/cache-joblib')
        self.memory = Memory(cache_dir, verbose=0)

    def cache_decorator(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.memory.cache(func)(*args, **kwargs)
        return wrapper


cache_decorator = CacheDecoratorJoblib().cache_decorator

query_ph_data = ("""SELECT * FROM look_product_level_1""")


class CacheManagerJoblib:

    @cache_decorator
    def query_ph_data(self):
        query = ("""SELECT * FROM look_product_level_1
                     where sku in (select distinct sku from stat_forecast_data_quantity)""")
        df = pd.read_sql_query(query, engine)
        return df

    @cache_decorator
    def query_df_daily_sales_oos(self, ph_data):
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
        daily_sales = daily_sales.merge(ph_data, on='sku', how='inner')
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
        daily_sales = pd.read_sql_query(query, engine)
        daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
        daily_sales['year'] = daily_sales['date'].dt.year
        daily_sales['month'] = daily_sales['date'].dt.month
        daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
        daily_sales['revenue'] = daily_sales['revenue'].astype(float)

        query_ph_data = ("""SELECT * FROM look_product_level_1""")
        ph_data = pd.read_sql_query(query_ph_data, engine)
        daily_sales = daily_sales.merge(ph_data, on='sku', how='inner')
        return daily_sales

    @cache_decorator
    def query_df_daily_sales(self):
        query = """
            SELECT * FROM agg_im_sku_daily_sales 
            WHERE sku IN (SELECT DISTINCT sku FROM look_product_hierarchy) 
            AND date > DATEADD(year, -3, GETDATE()) 
            ORDER BY sku, region, date;
            """
        df = pd.read_sql_query(query, engine)
        df['date'] = pd.to_datetime(df['date'])
        df['warehouse_code'] = df['region'].map(region_warehouse_codes)

        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_df_fc_qp(self):
        query = f"""SELECT stat.*
                        FROM stat_forecast_quantity_revenue stat
                        WHERE ds > DATEADD(day, -400, GETDATE()) 
                        ORDER BY ds, warehouse_code, region;"""
        df = pd.read_sql_query(query, engine)
        df['ds'] = pd.to_datetime(df['ds'])
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_df_running_stock(self):
        query = """
            select stat.* from stat_running_stock_forecast stat
                JOIN (
                    SELECT DISTINCT sku, warehouse_code 
                    FROM stat_forecast_data_quantity 
                ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
                WHERE ds >= CAST(GETDATE() AS DATE)
                """
        df = pd.read_sql_query(query, engine)
        df.date = pd.to_datetime(df.ds).dt.date
        df['ds'] = pd.to_datetime(df['ds'])
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_stockout_past(self):
        query = """SELECT stat.* FROM stat_stock_out_past stat
                JOIN (
                    SELECT DISTINCT sku, warehouse_code 
                    FROM stat_forecast_data_quantity 
                ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code"""
        df = pd.read_sql_query(query, engine)
        df.date = pd.to_datetime(df.date)
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_price_sensing_tab(self):
        query = """SELECT stat.* FROM stat_regression_coeff_price_quantity stat
                JOIN (
                    SELECT DISTINCT sku, warehouse_code 
                    FROM stat_forecast_data_quantity 
                ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code
                      order by price_elasticity desc"""
        df = pd.read_sql_query(query, engine)
        df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_price_regression_tab(self):
        query = """SELECT stat.* FROM  stat_regression_price_quantity stat
                JOIN (
                    SELECT DISTINCT sku, warehouse_code 
                    FROM stat_forecast_data_quantity 
                ) fcst ON fcst.sku = stat.sku AND fcst.warehouse_code = stat.warehouse_code"""
        df = pd.read_sql_query(query, engine)
        df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_price_reference(self):
        query = f"""SELECT stat.sku, stat.region,stat.price , stat.date
            FROM look_latest_price_reference stat
                JOIN (
                    SELECT sku, region, count(*) as count
                    FROM stat_forecast_data_quantity 
                    group by sku, region
                ) fcst ON fcst.sku = stat.sku and fcst.[region]=stat.region
                 and date > DATEADD(year, -1, GETDATE()) order by stat.sku, region, date;"""
        df = pd.read_sql_query(query, engine)
        df['date'] = pd.to_datetime(df['date'])
        ph_data=pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df

    @cache_decorator
    def query_price_recommender_summary(self):
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
        df = pd.read_sql_query(query, engine)
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
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
        ph_data = pd.read_sql_query(query_ph_data, engine)
        df = df.merge(ph_data, on='sku', how='inner')
        return df