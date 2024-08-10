# Description: This file contains the functions to get the data for price recommendation.
from config import price_recommendation_settings as cf
import pandas as pd
from common.db_connection import params
from sqlalchemy import create_engine, text
import diskcache as dc
from common.local_constants import region_warehouse_codes

cache = dc.Cache('cache-price-recommender')

def top_n_skus_revenue_last_3_months():
    engine =  create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)
    query = """
    select * from agg_im_sku_daily_sales 
    where sku in (select im_sku from look_product_hierarchy)
    """
    with engine.connect() as con:
        df_sales = pd.read_sql(text(query), con)

    df_sales['date'] = pd.to_datetime(df_sales['date'])
    df_sales['date_part'] = pd.to_datetime(df_sales['date'].dt.date)
    df_sales['month_year'] = df_sales['date'].dt.to_period('M')
    df_sales = df_sales[df_sales['date'] >= df_sales['date'].max() - pd.DateOffset(months=3)]
    df_sku_sales = df_sales.groupby(['sku'])['revenue'].sum().reset_index()
    df_sku_sales_sorted = df_sku_sales.sort_values(by='revenue', ascending=False)
    return df_sku_sales_sorted

def get_data_price_recommender():
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)
    query = """
    select * from stat_running_stock_forecast 
    WHERE ds >= CAST(GETDATE() AS DATE) 
    AND sku in (SELECT DISTINCT sku FROM stat_forecast_data_quantity);
    """
    with engine.connect() as con:
        df_running_stock= pd.read_sql(text(query),con)

    df_running_stock['ds'] = pd.to_datetime(df_running_stock['ds'])
    df_running_stock=df_running_stock[pd.notna(df_running_stock['running_stock_after_forecast'])]
    df_running_stock=df_running_stock.drop(columns=['Expected_Arrival_Date','status_date'])
    df_running_stock.sort_values(['sku','warehouse_code','ds'],inplace=True)

    query = """
    select sku, region, avg(price) as ref_price from look_latest_price_reference group by sku, region"""
    with engine.connect() as con:
        df_price_reference = pd.read_sql(text(query),con)
    df_price_reference['warehouse_code'] = df_price_reference['region'].replace(region_warehouse_codes)
    df_price_reference.drop(columns=['region'], inplace=True)
    df_price_reference = df_price_reference.groupby(['sku', 'warehouse_code']).agg({'ref_price': 'mean'}).reset_index()

    query = """
    select * from stat_regression_coeff_avg_price_quantity"""

    with engine.connect() as con:
        df_price_elasticity = pd.read_sql(text(query),con)
    df_running_stock = pd.merge(df_running_stock, df_price_reference, how='left', on=['sku', 'warehouse_code'])
    df_price_recommender = pd.merge(df_running_stock, df_price_elasticity, how='left', on=['sku', 'warehouse_code'])
    return df_price_recommender

def calculate_adjusted_price_stock( df):
    df['running_stock_after_forecast_adj'] = 0.0
    running_stock = 0.0

     # Loop through the DataFrame
    for index, row in df.iterrows():
        # Update running stock
        if index == df.first_valid_index():
            running_stock = row['running_stock_after_forecast'] + row['InTransit_Quantity']
        else:
            running_stock += row['InTransit_Quantity']

        predicted_sales = row['q_prime']

        if running_stock < predicted_sales:
            # If total stock is less than predicted sales, no sales occur
            df.at[index, 'running_stock_after_forecast_adj'] = 0.0
            running_stock = 0.0
        else:
            # Sales occur as predicted
            df.at[index, 'running_stock_after_forecast_adj'] = running_stock - predicted_sales
            running_stock -= predicted_sales

    return df