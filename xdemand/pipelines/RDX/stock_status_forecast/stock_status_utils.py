import pandas as pd
from common.db_connection import engine
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import text
from common.logger_ import get_logger
from common.local_constants import region_warehouse_codes
from config import price_recommendation_settings as pr_cf
from config import stock_status_settings as ss_cf
from common.cache_manager_joblib import CacheManagerJoblib
cache_manager = CacheManagerJoblib()

logger=get_logger()



def plot_warehouse_stock(df, sku):
    # Filter data for the given SKU
    sku_df = df[df['sku'] == sku]

    # Unique warehouse codes
    warehouse_codes = sku_df['warehouse_code'].unique()

    # Plotting
    for warehouse_code in warehouse_codes:
        warehouse_df = sku_df[sku_df['warehouse_code'] == warehouse_code]

        # Sort by date for plotting
        warehouse_df = warehouse_df.sort_values('ds')

        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Plot 'yhat' with ax1, on the left y-axis
        sns.lineplot(x='ds', y='yhat', data=warehouse_df, ax=ax1, color='blue', label='Forecasted daily dales')
        ax1.set_ylabel('Forecasted daily sales ', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1.set_ylim(0, warehouse_df['yhat'].max() * 1.1)  # Set minimum to 0 and max slightly above the max value


        # Create a second y-axis for 'running_stock_after_forecast'
        ax2 = ax1.twinx()
        sns.lineplot(x='ds', y='running_stock_after_forecast', data=warehouse_df, ax=ax2, color='green', label='Running Stock After Forecast')
        ax2.set_ylabel('Running Stock After Forecast', color='green')
        ax2.tick_params(axis='y', labelcolor='green')
        ax2.set_ylim(0, warehouse_df['running_stock_after_forecast'].max() * 1.1)  # Set minimum to 0 and max slightly above the max value


        # Highlighting the Expected Arrival Dates
        for _, row in warehouse_df.dropna(subset=['Expected_Arrival_Date']).iterrows():
            ax2.axvline(pd.to_datetime(row['Expected_Arrival_Date']), color='red', linestyle='--', lw=1)
            ax2.text(pd.to_datetime(row['Expected_Arrival_Date']), ax2.get_ylim()[1], f'  {int(row["InTransit_Quantity"])}', color='red', verticalalignment='top')

        plt.title(f'Stock Status for SKU {sku} at Warehouse {warehouse_code}')
        plt.xlabel('Date')
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.show()


def compute_stock_status(df):
    # Ensure that df has the required columns
    if not all(col in df.columns for col in ['Available', 'InTransit_Quantity', 'yhat']):
        raise ValueError("DataFrame missing one or more required columns")

    # Initialize new column
    df['stock_status'] = 0.0
    running_stock = 0.0

    # Loop through the DataFrame
    for index, row in df.iterrows():
        # Update running stock
        if index == df.first_valid_index():
            running_stock = row['Available'] + row['InTransit_Quantity']
        else:
            running_stock += row['InTransit_Quantity']


        predicted_sales = row['yhat']

        if running_stock < predicted_sales:
            # If total stock is less than predicted sales, no sales occur
            df.at[index, 'stock_status'] = 0.0
            running_stock = 0.0
        else:
            # Sales occur as predicted
            df.at[index, 'stock_status'] = running_stock - predicted_sales
            running_stock -= predicted_sales

    return df

def get_forecast_quantity_warhouse(sku=None):
    # Perform queries and load the result directly into pandas DataFrames
    if sku is not None:
        query_fc = f"SELECT * FROM stat_forecast_data_quantity where sku = '{sku}'"
    else:
        query_fc = f"SELECT * FROM stat_forecast_data_quantity"
    with engine.connect() as con:
        forecast_data = pd.read_sql(text(query_fc),con)

    # Explicitly name the columns to group by (excluding 'region')
    group_by_columns = ['ds', 'sku', 'last_data_seen', 'warehouse_code']  # Add other non-numerical columns as needed

    # Group by the specified columns and sum numerical columns
    forecast_warehouse = forecast_data.drop(columns=['yhat_lower','yhat_upper']).\
        groupby(group_by_columns).sum().reset_index()
    forecast_warehouse['yhat'] = forecast_warehouse['yhat'] * ss_cf.amazon_shopify_factor
    forecast_warehouse['trend'] = forecast_warehouse['trend'] * ss_cf.amazon_shopify_factor
    forecast_warehouse['yearly_seasonality'] = forecast_warehouse['yearly'] * ss_cf.amazon_shopify_factor
    # Convert the 'ds' column to datetime
    forecast_warehouse['ds'] = pd.to_datetime(forecast_warehouse['ds'])
    return forecast_warehouse

def get_forecast_revenue_warhouse(sku=None):
    # Perform queries and load the result directly into pandas DataFrames
    if sku is not None:
        query_fc = f"SELECT * FROM stat_forecast_data_revenue where sku = '{sku}'"
    else:
        query_fc = f"SELECT * FROM stat_forecast_data_revenue"
    with engine.connect() as con:
        forecast_data = pd.read_sql(text(query_fc),con)

    # Explicitly name the columns to group by (excluding 'region')
    group_by_columns = ['ds', 'sku', 'last_data_seen', 'warehouse_code']  # Add other non-numerical columns as needed

    # Group by the specified columns and sum numerical columns
    forecast_warehouse = forecast_data.drop(columns=['yhat_lower','yhat_upper']).\
        groupby(group_by_columns).sum().reset_index()
    forecast_warehouse['yhat'] = forecast_warehouse['yhat'] * ss_cf.amazon_shopify_factor
    forecast_warehouse['trend'] = forecast_warehouse['trend'] * ss_cf.amazon_shopify_factor
    forecast_warehouse['yearly_seasonality'] = forecast_warehouse['yearly'] * ss_cf.amazon_shopify_factor
    # Convert the 'ds' column to datetime
    forecast_warehouse['ds'] = pd.to_datetime(forecast_warehouse['ds'])
    return forecast_warehouse

def get_product_hierarchy_forecast_skus(formatted_skus,sku=None):

    # Perform queries and load the result directly into pandas DataFrames
    query_ph=f"""select * from look_product_hierarchy where im_sku IN ({formatted_skus})"""
    with engine.connect() as con:
        product_hierarchy = pd.read_sql_query(text(query_ph), con)
    product_hierarchy['im_sku'].nunique()
    product_hierarchy['im_sku']=product_hierarchy['im_sku'].astype(str)
    return product_hierarchy

def get_latest_stock_status_forecast_skus(formatted_skus):
    # Perform queries and load the result directly into pandas DataFrames
    query_st=f"SELECT * FROM latest_stock_status where im_sku IN ({formatted_skus})"
    with engine.connect() as con:
        stocks=pd.read_sql_query(text(query_st), con)
        stocks['log_date'] = pd.to_datetime(stocks['UploadDate_MAX'])
    return stocks

def get_shipments_after_log_date_forecast_skus(max_stock_date,formatted_skus):
    # Get shipments data
    query_ship=f"SELECT * FROM container_item_data WHERE Expected_Arrival_Date > '{max_stock_date}' and im_sku IN ({formatted_skus})"
    with engine.connect() as con:
        shipments = pd.read_sql_query(text(query_ship), con)
    shipments['warehouse_codes'] = shipments['WareHouseCode'].replace(region_warehouse_codes)
    return shipments


def get_forecast_stocks_shipments(sku=None):

    logger.info("Get Forecast Quantity with Warehouse Code")
    # Get forecast quantity with warehouse code
    # if you want to see the results for a specific SKU, add the SKU to the function call
    forecast_warehouse=get_forecast_quantity_warhouse(sku)
    forecast_warehouse_revenue=get_forecast_revenue_warhouse(sku)
    # merge forecast_warehouse and forecast_warehouse_revenue on ds, sku, warehouse_code
    # and get the revenue column from forecast_warehouse_revenue
    forecast_warehouse = pd.merge(forecast_warehouse,
                                  forecast_warehouse_revenue[['ds', 'sku', 'warehouse_code', 'yhat']],
                                  on=['ds', 'sku', 'warehouse_code'], suffixes=('', '_revenue'))
    logger.info("Get distinct SKUs present in Forecast Quantity")
    # Get distinct SKUs
    distinct_skus = forecast_warehouse['sku'].unique()
    # Convert each SKU to a string format suitable for SQL query
    formatted_skus = ', '.join(f"'{sku}'" for sku in distinct_skus)
    logger.info(f"{forecast_warehouse['sku'].nunique()} distinct SKUs present in Forecast Quantity")


    logger.info("Get Latest Stock Status for SKUs")
    stocks=get_latest_stock_status_forecast_skus(formatted_skus)
    logger.info(f"{stocks['im_sku'].nunique()} distinct SKUs present in Latest Stock Status")

    # Set the max date in your stocks data
    max_stock_date = stocks['log_date'].max()
    max_stock_date_str = max_stock_date.strftime('%Y-%m-%d')
    #forecast_warehouse[forecast_warehouse['ds'] > max_stock_date].to_csv('forecast_warehouse.csv')

    logger.info("Get Shipments after Log Date for SKUs")
    shipments=get_shipments_after_log_date_forecast_skus(max_stock_date_str,formatted_skus)
    logger.info(f"{shipments['im_sku'].nunique()} distinct SKUs present in Shipments")


    logger.info("Get Stock Status after Forecast")
    # Filter forecast_warehouse for dates greater than max_stock_date
    forecast_filtered = forecast_warehouse[forecast_warehouse['ds'] > max_stock_date]
    forecast_filtered=forecast_filtered.sort_values(['warehouse_code','sku','ds',])
    # rename yhat_revenue to revenue
    forecast_filtered.rename(columns={'yhat_revenue': 'revenue'}, inplace=True)
    return forecast_filtered,stocks,shipments
def merge_shiptment_stocks_forecast(shipments,stocks,forecast_filtered):
    # Set the max date in your stocks data
    max_stock_date = stocks['log_date'].max()
    max_stock_date_str = max_stock_date.strftime('%Y-%m-%d')
    # Merge with stocks DataFrame and calculate stock status
    merged_df = pd.merge(forecast_filtered, stocks, how='left', left_on=['sku', 'warehouse_code'],
                         right_on=['im_sku', 'WareHouseCode'])
    merged_df = pd.merge(merged_df, shipments, how='left', left_on=['sku', 'warehouse_code', 'ds'],
                         right_on=['im_sku', 'warehouse_codes', 'Expected_Arrival_Date'])
    merged_df['InTransit_Quantity'] = merged_df['InTransit_Quantity'].fillna(0)
    merged_df.sort_values(['warehouse_code', 'sku', 'ds'], inplace=True)
    merged_df = merged_df.groupby(['sku', 'warehouse_code']).apply(compute_stock_status)
    # merged_df['running_stock_after_forecast']= merged_df.groupby(['sku', 'warehouse_code']).apply(compute_stock_status)
    merged_df['running_stock_after_forecast'] = merged_df['stock_status']
    # Calculate average yhat for each SKU and warehouse combination
    # drop merged_df index
    merged_df = merged_df.reset_index(drop=True)
    avg_yhat = merged_df.groupby(['sku', 'warehouse_code'])['yhat'].mean().reset_index()
    merged_df['is_understock'] = merged_df['running_stock_after_forecast'] < merged_df['yhat']
    # apply is_overstock condition based on the average yhat for each SKU and warehouse combination
    merged_df = pd.merge(merged_df, avg_yhat, on=['sku', 'warehouse_code'], suffixes=('', '_avg'))
    merged_df['is_overstock'] = merged_df['running_stock_after_forecast'] > (merged_df['yhat_avg']*(60+pr_cf.forecast_stock_level))
    merged_df = merged_df[
        ['ds', 'sku', 'warehouse_code', 'yhat', 'trend', 'yearly_seasonality', 'revenue',
         'running_stock_after_forecast', 'is_understock', 'is_overstock','Expected_Arrival_Date',
         'InTransit_Quantity']]
    merged_df['status_date'] = max_stock_date
    logger.info(f"Max Stock Status Date Processed {max_stock_date}")
    return merged_df