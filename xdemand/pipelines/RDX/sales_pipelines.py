import logging
import sys
import warnings

from common.db_connection import write_replace_db
from config import forecast_settings as pf_cf
from config import price_sensing_settings as ps_cf
from xdemand.pipelines.RDX.price_sensing.elasticity_log_ST_adjusted import get_price_elasticity
from xdemand.pipelines.RDX.price_sensing.ps_utils import get_daily_sales_price_sensing
from xdemand.pipelines.RDX.price_sensing.ps_utils import std_price_regression
from xdemand.pipelines.RDX.sales_forecast.forecast_utils import add_holidays
from xdemand.pipelines.RDX.sales_forecast.forecast_utils import forecast_sales
from xdemand.pipelines.RDX.sales_forecast.forecast_utils import get_daily_sales_proecessed
from xdemand.preprocessing.RDX.sql.execute_preprocessing_sql import preprocess_marketplace_sales_to_im_sales
from xdemand.pipelines.RDX.stockout_detection.stockout_detection import run_stockout_detection
sys.path.append('/opt/homebrew/lib')
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_prophet_training_pipeline():
    warnings.filterwarnings("ignore")
    logger.info("Starting Sales Forecasting Pipeline")
    daily_sales = get_daily_sales_proecessed()
    # get daily sales
    max_date = max(daily_sales['date_part'])

    logger.info("sku count after filtering for 100 rows")
    logger.info(daily_sales['sku'].nunique())
    grouper = daily_sales.groupby(['region', 'sku'])

    for target in pf_cf.target_cols:
        # Forecast sales for all SKU, region combinations
        forecasts = forecast_sales(grouper, target, max_date)
        # Add holidays to the forecast
        forecasts = add_holidays(forecasts, max_date)
        # Write to the database
        write_replace_db(forecasts, f"stat_forecast_data_{target}")
        logger.info(f"Saved forecasts to database for target {target}")

    # add date of processing (current time) to logger
    logger.info("sku Prossesesed Count")
    logger.info(daily_sales['sku'].nunique())

def run_price_sensing_direct():
    logger.info("Starting Price Sensing Pipeline")

    # Get daily sales and price sensing data
    df_dsa = get_daily_sales_price_sensing()
    # log parameters
    logger.info(f"Parameters for regression, {ps_cf.top_n} top n, {ps_cf.regressor} regressors,  {ps_cf.target} target")
    max_date = max(df_dsa['date'])
    df_dsa['date_part'] = df_dsa['date'].dt.date
    # log min and max dates
    logger.info(f"Max date {max_date} and min date {df_dsa['date'].min()}")

    # Get price elasticity
    reg_coef_df = get_price_elasticity(df_dsa)
    logger.info(f"price elasticity df head {reg_coef_df.head()}")
    log_normal_regressions = std_price_regression(df_dsa)
    logger.info(f"log_normal_regressions.head() {log_normal_regressions.head()}")


    # Write regression coefficients and results to the database
    write_replace_db(reg_coef_df, f'stat_regression_coeff_{ps_cf.regressor}_{ps_cf.target}')
    write_replace_db(log_normal_regressions, f'stat_regression_{ps_cf.regressor}_{ps_cf.target}')
    logger.info(f"Saved regression results to database for regressor {ps_cf.regressor} and target {ps_cf.target}")
    return

if __name__ == '__main__':
    logger.info("Starting RDX Pipeline")
    preprocess_marketplace_sales_to_im_sales()
    run_prophet_training_pipeline()
    run_stockout_detection()
    run_price_sensing_direct()