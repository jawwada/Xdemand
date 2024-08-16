from datetime import datetime
from datetime import timedelta
import logging
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression

from common.local_constants import region_warehouse_codes
from config import price_sensing_settings as cf
from common.cache_manager import CacheManager

cache_manager = CacheManager()
target = cf.target
regressor = cf.regressor
top_n = cf.top_n
days_before = cf.days_before
log_normal_regression = cf.log_normal_regression
plot = cf.plot

logger = logging.getLogger(__name__)

def filter_top_n(df_dsa):
    grouped = df_dsa.groupby('sku')['revenue'].sum()
    # Sort the summed quantities in descending order and take the top 100
    top_products = grouped.sort_values(ascending=False).head(cf.top_n)
    # Filter the original DataFrame for only the top 100 SKUs
    df_dsa = df_dsa[df_dsa['sku'].isin(top_products.index)]
    return df_dsa

def process_reference_price():
    # process reference price
    df_price_reference = cache_manager.query_price_reference()
    df_price_reference['warehouse_code'] = df_price_reference['region'].map(region_warehouse_codes)
    # drop region column and average price over warehouse_code
    df_price_reference.drop(columns=['region'], inplace=True)
    df_price_reference = df_price_reference.groupby(['sku', 'warehouse_code']).agg({'ref_price': 'mean'}).reset_index()
    return df_price_reference

def daily_sales_price_sensing_transform(df_dsa):
    df_dsa['date'] = pd.to_datetime(df_dsa['date'])
    # Filter data based on the top_n parameter
    df_dsa = filter_top_n(df_dsa)
    # Calculate the average price and promotional rebates
    df_dsa['price'] = (df_dsa['revenue'] - df_dsa['promotional rebates']) / (df_dsa['quantity']+0.00001)
    df_price_reference=process_reference_price()
    df_dsa = pd.merge(df_dsa, df_price_reference, how='left', on=['sku', 'warehouse_code'])
    return df_dsa


def std_price_regression(df_dsa):
    target = cf.target
    regressor = 'avg_price'
    days_before = cf.days_before
    log_normal_regression = cf.log_normal_regression
    plot = cf.plot
    # Filter data based on the days_before parameter
    days_ago = datetime.today() - timedelta(days=days_before)
    df_filtered = df_dsa[df_dsa['date'] > days_ago]
    # Filter the original data to include only the top N SKUs
    df_top_skus = df_filtered
    # Get a list of unique SKUs
    unique_skus = df_top_skus['sku'].unique()
    # Initialize DataFrames to store regression coefficients and all regressions
    all_regressions_list = []
    # Iterate through each unique SKU and fit a linear regression model
    for sku in unique_skus:
        df_sku = df_top_skus[(df_top_skus['sku'] == sku)]
        unique_wh = df_sku['warehouse_code'].unique()
        for warehouse in unique_wh:
            # put the code in try except block so that if data is not available for a particular sku and warehouse
            # it will not stop the execution
            try:
                # Filter the data for the current SKU

                df_sku_wh = df_sku[(df_sku['warehouse_code'] == warehouse)].copy()
                # drop na
                df_sku_wh.dropna(subset=[target, regressor], inplace=True)
                # Prepare data for regression
                # Calculate the mean and standard deviation of the target variable
                mean_regresor = df_sku_wh['ref_price'].mean()
                std_regresor = df_sku_wh[regressor].std()

                lower_bound = mean_regresor - cf.regressor_lower_bound * std_regresor
                upper_bound = max(mean_regresor + cf.regressor_upper_bound * std_regresor, 0)
                # Generate values within this range
                X = np.linspace(lower_bound, upper_bound, 100)[::-1].reshape(-1, 1)

                target_col = df_sku_wh[target]
                mean_target = target_col.mean()
                std_target = target_col.std()

                # Define the range as mean ± 2 standard deviations
                lower_bound = mean_target - cf.target_lower_bound * std_target
                upper_bound = max(mean_target + cf.target_lower_bound * std_target, 0)

                # Generate values within this range
                y = np.linspace(lower_bound, upper_bound, 100).reshape(-1, 1)
                small_positive_number = 1e-10
                y = np.where((y > 0) & (~np.isnan(y)), y, small_positive_number)
                y = np.log(y) if log_normal_regression else y
                # Fit a linear regression model
                reg = LinearRegression().fit(X, y)

                X_pred = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)  # 100 points for smooth line
                y_pred = reg.predict(X_pred)
                idx = np.array(range(0, 100)).reshape(-1, 1)
                # Applying inverse log to predictions if necessary
                small_positive_number = 1e-10
                y_pred = np.where((y_pred > 0) & (~np.isnan(y_pred)), y_pred, small_positive_number)
                y_pred = np.exp(y_pred) if log_normal_regression else y_pred
                # Append results to DataFrames
                for id, x_val, y_val in zip(idx, X_pred, y_pred):
                    all_regressions_list.append(
                        {'idx': id, 'sku': sku, 'warehouse_code': warehouse, 'x_pred': x_val.item(),
                         'y_pred': y_val.item()})
            except:
                logger.info(f"Data not available for sku {sku} and warehouse {warehouse}")
                continue

    all_regressions = pd.concat([pd.DataFrame(d) for d in all_regressions_list], ignore_index=True)

    all_regressions['measure_sense'] = target
    all_regressions['type_sense'] = regressor
    all_regressions['last_data_seen'] = df_filtered['date'].max()
    all_regressions['log_normal_regression'] = log_normal_regression
    # Convert the dictionary to a DataFrame and sort by the regression coefficients
    # add measure sense and target

    return all_regressions
