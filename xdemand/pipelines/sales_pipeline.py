import platform
from typing import List

import pandas as pd

from common.cache_manager import CacheManager
from common.db_connection import engine
from common.db_connection import write_replace_db
from common.db_connection import write_replace_db
from common.db_connection import write_replace_db
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from scripts.sales_pipelines import logger
from xdemand.pipelines.RDX.price_sensing.elasticity_log_ST_adjusted import get_price_elasticity
from xdemand.pipelines.RDX.price_sensing.ps_utils import daily_sales_price_sensing_transform
from xdemand.pipelines.RDX.price_sensing.ps_utils import filter_top_n
from xdemand.pipelines.RDX.price_sensing.ps_utils import std_price_regression
from xdemand.pipelines.RDX.sales_forecast.execute_preprocessing_sql import preprocess_marketplace_sales_to_im_sales
from xdemand.pipelines.RDX.sales_forecast.forecast_utils import add_holidays
from xdemand.pipelines.RDX.sales_forecast.forecast_utils import forecast_sales
from xdemand.pipelines.RDX.sales_forecast.forecast_utils import prophet_pipeline_daily_sales_transform
from xdemand.pipelines.RDX.stockout_detection.stockout_detection_utils import fill_missing_dates
from xdemand.pipelines.RDX.stockout_detection.stockout_detection_utils import get_total_days_dict
from xdemand.pipelines.RDX.stockout_detection.stockout_detection_utils import preprocess_dataframe
from xdemand.pipelines.RDX.stockout_detection.stockout_detection_utils import process_sku_warehouse_combinations
from xdemand.pipelines.RDX.stockout_detection.stockout_detection_utils import visualize_stockout


class SalesPipeline:
    def __init__(self,
                 top_n: int = 10,
                 write_to_db: bool = True,
                 plot: bool = False,
                 min_rows_per_sku: int = 365,
                 forecast_periods: int = 180,
                 forecast_period_freq: str = 'D',
                 target_cols: List[str] = None,
                 forecast_tail_periods: int = 550,
                 # Parameters from price_sensing_direct.yaml
                 price_plot: bool = True,
                 log_normal_regression: bool = True,
                 regressor_lower_bound: int = 2,
                 regressor_upper_bound: int = 2,
                 target_lower_bound: int = 1,
                 target_upper_bound: int = 2,
                 price_target: str = 'quantity',
                 price_write_to_db: bool = True,
                 regressor: str = 'avg_price',
                 days_before: int = 365):

        self.cache_manager = CacheManager()
        self.top_n = top_n
        self.write_to_db = write_to_db
        self.plot = plot
        self.min_rows_per_sku = min_rows_per_sku
        self.forecast_periods = forecast_periods
        self.forecast_period_freq = forecast_period_freq
        self.target_cols = target_cols or ['quantity', 'revenue']
        self.forecast_tail_periods = forecast_tail_periods

        # Price sensing parameters
        self.price_plot = price_plot
        self.log_normal_regression = log_normal_regression
        self.regressor_lower_bound = regressor_lower_bound
        self.regressor_upper_bound = regressor_upper_bound
        self.target_lower_bound = target_lower_bound
        self.target_upper_bound = target_upper_bound
        self.price_target = price_target
        self.price_write_to_db = price_write_to_db
        self.regressor = regressor
        self.days_before = days_before

    def run_prophet_training_pipeline(self):
        """Runs the sales forecasting pipeline using the Prophet model."""
        logger.info("Starting Sales Forecasting Pipeline")
        sales_df = self.cache_manager.query_df_daily_sales()
        daily_sales = prophet_pipeline_daily_sales_transform(sales_df)
        max_date = max(daily_sales['date_part'])

        logger.info("SKU count after filtering for 100 rows")
        logger.info(daily_sales['sku'].nunique())
        grouper = daily_sales.groupby(['region', 'sku'])

        for target in self.target_cols:
            forecasts = forecast_sales(grouper, target, max_date)
            forecasts = add_holidays(forecasts, max_date)
            forecasts['warehouse_code'] = forecasts['region'].map(region_warehouse_codes)
            if self.write_to_db:
                write_replace_db(forecasts, f"stat_forecast_data_{target}")
            logger.info(f"Saved forecasts to database for target {target}")

        logger.info("SKU Processed Count")
        logger.info(daily_sales['sku'].nunique())

    def run_price_sensing_direct(self):
        """Runs the price sensing pipeline to analyze price elasticity and sales data."""
        logger.info("Starting Price Sensing Pipeline")
        df_dsa = self.cache_manager.query_df_daily_sales_forecast_skus()
        logger.info(f"df_dsa head {df_dsa.head()}")
        df_dsa = df_dsa.groupby(['channel', 'sku', 'warehouse_code', 'date'])[
            ['quantity', 'revenue', 'promotional rebates']].sum().reset_index()
        df_dsa = filter_top_n(df_dsa)
        df_dsa = daily_sales_price_sensing_transform(df_dsa)
        logger.info(
            f"Parameters for regression, {self.top_n} top n, {self.regressor} regressors, {self.price_target} target")
        max_date = max(df_dsa['date'])
        df_dsa['date_part'] = df_dsa['date'].dt.date
        logger.info(f"Max date {max_date} and min date {df_dsa['date'].min()}")

        reg_coef_df = get_price_elasticity(df_dsa)
        logger.info(f"Price elasticity df head {reg_coef_df.head()}")
        reg_coef_df['price_elasticity'] = reg_coef_df['price_elasticity'].clip(lower=self.regressor_lower_bound,
                                                                               upper=self.regressor_upper_bound)
        log_normal_regressions = std_price_regression(df_dsa)
        logger.info(f"log_normal_regressions.head() {log_normal_regressions.head()}")

        if self.price_write_to_db:
            write_replace_db(reg_coef_df, f'stat_regression_coeff_{self.regressor}_{self.price_target}')
            write_replace_db(log_normal_regressions, f'stat_regression_{self.regressor}_{self.price_target}')
        logger.info(
            f"Saved regression results to database for regressor {self.regressor} and target {self.price_target}")

    def run_stockout_detection(self):
        """Detects stockouts based on sales data and fills in missing dates."""
        logger.info("Starting Stockout Detection Pipeline")
        df = self.cache_manager.query_df_daily_sales_forecast_skus()
        df = df.groupby(['channel', 'sku', 'warehouse_code', 'date'])[['quantity']].sum().reset_index()
        df_filled = df.groupby(['channel', 'sku', 'warehouse_code']).apply(fill_missing_dates).reset_index(drop=True)
        df_filled['quantity'] = df_filled['quantity'].fillna(0)
        total_days_dict = get_total_days_dict(df_filled)
        grid_df = df_filled.copy(deep=True)
        grid_df['gaps'] = (~(grid_df['quantity'] > 0)).astype(int)
        grid_df = process_sku_warehouse_combinations(grid_df, total_days_dict)
        numeric_columns = ['quantity', 'gaps', 'gap_days', 'gap_e', 'sale_prob', 'gap_e_log10']
        grid_df[numeric_columns] = grid_df[numeric_columns].apply(pd.to_numeric, errors='coerce')
        grid_df = grid_df[
            ['channel', 'sku', 'warehouse_code', 'date', 'quantity', 'gaps', 'gap_days', 'gap_e', 'sale_prob',
             'gap_e_log10']]
        grid_df['out_of_stock'] = grid_df['gap_e_log10'] >= 2
        grid_df = preprocess_dataframe(grid_df)
        grid_df.to_sql('stat_stock_out_past', engine, if_exists='replace', index=False)
        if platform.system() == 'Windows' or platform.system() == 'Darwin':
            visualize_stockout(grid_df)

    def run_all_pipelines(self):
        """Runs all pipelines in sequence: preprocessing, forecasting, stockout detection, and price sensing."""
        preprocess_marketplace_sales_to_im_sales()
        self.run_prophet_training_pipeline()
        self.run_stockout_detection()
        self.run_price_sensing_direct()
        logger.info("All pipelines completed")
