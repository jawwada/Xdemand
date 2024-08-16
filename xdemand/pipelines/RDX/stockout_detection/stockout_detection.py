import warnings
import platform
import pandas as pd
import numpy as np

from common.db_connection import engine
from xdemand.pipelines.RDX.stockout_detection.stockout_detection_utils import fill_missing_dates, \
    process_sku_warehouse_combinations, visualize_stockout, get_total_days_dict

from common.cache_manager import CacheManagerFlask



# Ignore warnings
warnings.filterwarnings('ignore')

def run_stockout_detection():
    """
    Main function to execute the stockout detection process.
    """
    # Fetch daily sales data
    cache_manager = CacheManagerFlask()
    df = cache_manager.query_df_daily_sales()
    df = df.groupby(['channel', 'sku', 'warehouse_code','level_1', 'date'])[['quantity']].sum().reset_index()

    # Fill missing dates for each SKU and warehouse combination
    df_filled = df.groupby(['channel', 'sku', 'warehouse_code','level_1']).apply(fill_missing_dates).reset_index(drop=True)
    df_filled['quantity'] = df_filled['quantity'].fillna(0)

    # Calculate total days dictionary
    total_days_dict = get_total_days_dict(df_filled)

    # Initialize lists to hold results
    grid_df = df_filled.copy(deep=True)
    grid_df['gaps'] = (~(grid_df['quantity'] > 0)).astype(int)

    # Process each SKU and warehouse combination
    grid_df = process_sku_warehouse_combinations(grid_df, total_days_dict)

    # Ensure all numeric columns are of the correct data type
    numeric_columns = ['quantity', 'gaps', 'gap_days', 'gap_e', 'sale_prob', 'gap_e_log10']
    grid_df[numeric_columns] = grid_df[numeric_columns].apply(pd.to_numeric, errors='coerce')

    grid_df = grid_df[
        ['channel','sku', 'warehouse_code','level_1', 'date', 'quantity', 'gaps', 'gap_days', 'gap_e', 'sale_prob', 'gap_e_log10']]
    # Add stockout column
    grid_df['out_of_stock'] = grid_df['gap_e_log10'] >= 2

    # Preprocess DataFrame to handle inf values
    grid_df = grid_df.replace([np.inf, -np.inf], None, inplace=True)

    # Save to database
    grid_df.to_sql('stat_stock_out_past', engine, if_exists='replace', index=False)

    # Visualization
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        visualize_stockout(grid_df)
    return
