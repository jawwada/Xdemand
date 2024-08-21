# Description: This file contains the functions to get the data for price recommendation.
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text

from common.cache_manager_joblib import CacheManagerJoblib
from common.db_connection import params

cache_manager = CacheManagerJoblib()


def top_n_skus_revenue_last_3_months():
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)
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
    df_running_stock = cache_manager.query_df_running_stock()

    df_running_stock['ds'] = pd.to_datetime(df_running_stock['ds'])
    df_running_stock = df_running_stock[pd.notna(df_running_stock['running_stock_after_forecast'])]
    df_running_stock = df_running_stock.drop(columns=['Expected_Arrival_Date', 'status_date'])
    df_running_stock.sort_values(['sku', 'warehouse_code', 'ds'], inplace=True)

    df_price_reference = cache_manager.query_price_reference()
    df_price_reference = df_price_reference.groupby(['sku', 'warehouse_code']).agg({'price': 'mean'}).reset_index()
    df_price_reference.rename(columns={'price': 'ref_price'}, inplace=True)
    df_price_elasticity = cache_manager.query_price_sensing_tab()
    df_running_stock = pd.merge(df_running_stock, df_price_reference, how='left', on=['sku', 'warehouse_code'])
    df_price_recommender = pd.merge(df_running_stock, df_price_elasticity, how='left',
                                    on=['sku', 'warehouse_code', 'level_1'])
    return df_price_recommender


def calculate_adjusted_price_stock(df):
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


def get_price_adjustments(name, group, p0, price_rec, r, cf):
    group_info = dict({
        'sku': name[0],
        'warehouse_code': name[1],
        'ref_price': group['ref_price'].mean(),
        'mean_demand': group['yhat'].mean(),
        'current_stock': group['running_stock_after_forecast'].head(1).item(),
        'opt_stock_level': 0.0,
        'inventory_orders': 0.0,
        'understock_days': group['is_understock'].sum(),
        'overstock_days': group['is_overstock'].sum(),
        'price_elasticity': group['price_elasticity'].mean()
    })
    group['q_prime'] = group['yhat'] * (price_rec / p0) ** r
    group = calculate_adjusted_price_stock(group)
    group['y_hat_adj'] = group['yhat'].where(group['yhat'] < group['running_stock_after_forecast'], 0)
    group['q_prime_adj'] = group['q_prime'].where(group['q_prime'] < group['running_stock_after_forecast_adj'], 0)
    revenue_before = group['y_hat_adj'].sum() * p0
    revenue_after = group['q_prime_adj'].sum() * price_rec
    # set up the df_sku_warehouse_info

    # prepare inventory orders , fir
    group_info['opt_stock_level'] = group_info['mean_demand'] * cf.forecast_stock_level
    # sum up the in trainst quantity for next cf.forecast_stock_level days
    in_transit_sum = group['InTransit_Quantity'].head(cf.forecast_stock_level).sum()
    group_info['inventory_orders'] = group_info['opt_stock_level'] - group_info['current_stock'] - in_transit_sum

    # Add new columns to the aggregated DataFrame
    group_info['revenue_before'] = revenue_before
    group_info['revenue_after'] = revenue_after
    group_info['price_new'] = price_rec
    group_info['price_old'] = p0
    df_group_info = pd.DataFrame(group_info, index=[0])
    print(revenue_before, revenue_after)
    return group, df_group_info
