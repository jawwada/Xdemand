import pandas as pd
from sqlalchemy import text

from common.db_connection import engine
from common.local_constants import region_warehouse_codes


# get daily sales
def get_daily_sales_and_forecast_melted():
    sales_query = """
    SELECT sku, region, date, quantity, revenue, [promotional rebates] as promotional_rebates
    FROM agg_im_sku_daily_sales
    WHERE date <= DATEADD(month , -13, GETDATE())
    """
    # cut the data 12 months back from max date in the data
    df_sales = pd.read_sql_query(text(sales_query), engine)
    df_sales['date'] = pd.to_datetime(df_sales['date'])

    max_date = df_sales['date'].max()
    df_sales = df_sales[df_sales['date'] <= max_date]

    #
    df_sales['warehouse_code'] = df_sales['region'].replace(region_warehouse_codes)

    df_sales = df_sales.drop(columns=['region'])
    # group by sku, warehouse and date and sum the quantity and revenue
    df_sales = df_sales.groupby(['sku', 'warehouse_code', 'date']).sum().reset_index()
    df_sales['avg_price'] = (df_sales['revenue'] - df_sales['promotional_rebates']) / df_sales['quantity']
    df_sales['avg_price'] = df_sales['avg_price'].fillna(method='ffill').fillna(method='bfill')
    df_sales = df_sales.drop(columns=['promotional_rebates'])

    # melt the data so that we have monthly sales for each sku, warehouse
    df_sales = df_sales.pivot_table(index=['sku', 'warehouse_code'], columns='date', values='quantity').reset_index()
    # fill the missing values with 0
    df_sales = df_sales.fillna(0)

    #  get the last month end and its last date and cut off the data to that data
    last_month_end = max_date.get_month_beginning() - pd.DateOffset(days=1)
    df_sales = df_sales[df_sales['date'] <= last_month_end]

    # get the forecasted data
    forecast_query = """
    SELECT [sku]
      ,[region]
      ,[warehouse_code]
      ,[ds] as date
      ,[quantity]
      ,[revenue] FROM [dbo].[stat_forecast_quantity_revenue] """
    df_forecast = pd.read_sql_query(text(forecast_query), engine)
    df_forecast['date'] = pd.to_datetime(df_forecast['date'])

    df_forecast = df_forecast[df_forecast['date'] > last_month_end]
    # get average price and fill the missing values
    df_forecast['avg_price'] = df_forecast['revenue'] / df_forecast['quantity']
    df_forecast['avg_price'] = df_forecast['avg_price'].fillna(method='ffill').fillna(method='bfill')
    # get both the columns in the same order and concatenate the data
    df_forecast = df_forecast[['sku', 'warehouse_code', 'date', 'quantity', 'avg_price']]
    df_sales = df_sales[['sku', 'warehouse_code', 'date', 'quantity', 'avg_price']]
    return df_sales, df_forecast


# get running stock
def get_running_stock(understock_threshold_days=90, overstock_threshold_days=150, min_stock=20):
    stock_query = """
    SELECT *
        FROM stat_running_stock_forecast
        WHERE ds <= DATEADD(DAY, 183, GETDATE())
    """
    df_stock = pd.read_sql_query(text(stock_query), engine)
    df_stock['ds'] = pd.to_datetime(df_stock['ds'])
    return df_stock


def get_lookups():
    ph_query = """
    SELECT im_sku as sku, level_1 as category
    FROM look_product_hierarchy
    """
    df_ph = pd.read_sql_query(text(ph_query), engine)
    df_ph['sku'] = df_ph['sku'].astype(str)

    product_lead_time_query = """
    SELECT linnworks_sku as sku, product_lead_time_days as lead_time
    FROM look_product_lead_time
    """
    df_lead_time = pd.read_sql_query(text(product_lead_time_query), engine)
    df_lead_time['sku'] = df_lead_time['sku'].astype(str)
    df_ph = df_ph.merge(df_lead_time, on='sku', how='left')
    df_ph['lead_time'] = df_ph['lead_time'].fillna(90)

    reference_price_query = """
    SELECT sku, region, price as reference_price
    FROM look_latest_price_reference
    """
    df_price = pd.read_sql_query(text(reference_price_query), engine)
    df_price['warehouse_code'] = df_price['region'].replace(region_warehouse_codes)
    df_price = df_price.drop(columns=['region'])
    df_price = df_price.groupby(['sku', 'warehouse_code']).mean().reset_index()
    df_lookup = df_price.merge(df_ph, on='sku', how='left')

    df_price_elasticity = pd.read_sql_query(text('SELECT * FROM stat_regression_coeff_price_quantity'), engine)
    df_price_elasticity['sku'] = df_price_elasticity['sku'].astype(str)
    df_lookup = df_lookup.merge(df_price_elasticity, on=['sku', 'warehouse_code'], how='left')

    price_recommendation_query = """
    select sku, warehouse_code, revenue_before, revenue_after, price_new, price_old
    from stat_price_recommender_summary
    """
    df_price_rec = pd.read_sql_query(text(price_recommendation_query), engine)
    df_sku_warehouse_info = df_lookup.merge(df_price_rec, on=['sku', 'warehouse_code'], how='left')
    return df_sku_warehouse_info


df_sales, df_forecast = get_daily_sales_and_forecast_melted()
print(df_sales)

df_running = get_running_stock()
print(df_running)

df_lookups = get_lookups()
print(df_lookups)
