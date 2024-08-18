from common.db_connection import write_replace_db
from common.logger_ import logger
from config import forecast_settings as cf
from xdemand.pipelines.RDX.sales_forecast.porphet_forecaster import add_holidays
from xdemand.pipelines.RDX.sales_forecast.porphet_forecaster import forecast_sales
from xdemand.pipelines.RDX.sales_forecast.porphet_forecaster import prophet_pipeline_daily_sales_transform
from xdemand.pipelines.RDX.stockout_detection.stockout_detection import stockout_detection


logger.info("Starting Sales Forecasting Pipeline")
daily_sales = prophet_pipeline_daily_sales_transform()
# get daily sales
max_date = max(daily_sales['date_part'])

logger.info("sku count after filtering for 100 rows")
logger.info(daily_sales['sku'].nunique())
grouper = daily_sales.groupby(['region', 'sku'])

for target in cf.target_cols:

    # Forecast sales for all SKU, region combinations
    forecasts = forecast_sales(grouper, target, max_date)
    # Add holidays to the forecast
    forecasts = add_holidays(forecasts, max_date)
    # Write to the database
    if cf.write_to_db:
        write_replace_db(forecasts, f"stat_forecast_data_{target}")
        logger.info(f"Saved forecasts to database for target {target}")
    else:
        logger.info("Running locally so not saving to DB")
        forecasts.to_csv('data/quantity_forecasts.csv', index=False)

# add date of processing (current time) to logger
logger.info("sku Prossesesed Count")
logger.info(daily_sales['sku'].nunique())
