import pandas as pd
from common.local_constants import region_warehouse_codes
from common.db_connection import engine

def query_ph_data():
    query = "SELECT * FROM look_product_hierarchy where im_sku in (select distinct sku from stat_forecast_data_quantity)"
    df = pd.read_sql_query(query, engine)
    df['sku'] = df.im_sku
    df['warehouse_code'] = df['region'].map(region_warehouse_codes)
    return df.to_json(date_format='iso', orient='split')

def query_df_daily_sales_oos():
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
    return daily_sales.to_json(date_format='iso', orient='split')

def query_df_daily_sales():
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
    return daily_sales.to_json(date_format='iso', orient='split')

def query_df_fc_qp():
    query = f"""SELECT * FROM stat_forecast_quantity_revenue
            WHERE sku IN (SELECT DISTINCT sku FROM stat_forecast_data_quantity) and ds > DATEADD(year, -1, GETDATE()) ORDER BY ds, sku, warehouse_code;"""
    df = pd.read_sql_query(query, engine)
    df['ds'] = pd.to_datetime(df['ds'])
    return df.to_json(date_format='iso', orient='split')

def query_df_running_stock():
    query = """
    select * from stat_running_stock_forecast
    WHERE ds >= CAST(GETDATE() AS DATE)
    AND sku in (SELECT DISTINCT sku FROM stat_forecast_data_quantity);
    """
    df = pd.read_sql_query(query, engine)
    df.date = pd.to_datetime(df.ds).dt.date
    df['ds'] = pd.to_datetime(df['ds'])
    return df.to_json(date_format='iso', orient='split')

def query_stockout_past():
    query = "SELECT * FROM stat_stock_out_past where sku in (select distinct sku from stat_forecast_data_quantity)"
    df = pd.read_sql_query(query, engine)
    df.date = pd.to_datetime(df.date)
    return df.to_json(date_format='iso', orient='split')

def query_price_sensing_tab():
    query = ("SELECT * FROM stat_regression_coeff_avg_price_quantity where"
             " sku in (select distinct sku from stat_forecast_data_quantity) order by price_elasticity desc")
    df = pd.read_sql_query(query, engine)
    df['price_elasticity'] = df['price_elasticity'].astype(float).round(4)
    return df.to_json(date_format='iso', orient='split')

def query_price_regression_tab():
    query = "SELECT * FROM  stat_regression_avg_price_quantity where sku in (select distinct sku from stat_forecast_data_quantity)"
    df = pd.read_sql_query(query, engine)
    return df.to_json(date_format='iso', orient='split')

def query_price_reference():
    query = f"""SELECT * FROM look_latest_price_reference
    where sku in (select distinct sku from stat_forecast_data_quantity) and date > DATEADD(year, -1, GETDATE()) order by sku, region, date;"""
    df = pd.read_sql_query(query, engine)
    df['date'] = pd.to_datetime(df['date'])
    return df.to_json(date_format='iso', orient='split')

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
    df = pd.read_sql_query(query, engine)
    return df.to_json(date_format='iso', orient='split')

def query_price_recommender():
    query = f"""SELECT
    [sku]
    , [ds]
    , [warehouse_code]
    , [InTransit_Quantity]
    , [running_stock_after_forecast_adj] as running_stock_after_forecast_adj
    , [q_prime_adj] as q_prime_adj
    FROM[dbo].[stat_price_recommender]"""
    df = pd.read_sql_query(query, engine)
    df['ds'] = pd.to_datetime(df['ds'])
    return df.to_json(date_format='iso', orient='split')