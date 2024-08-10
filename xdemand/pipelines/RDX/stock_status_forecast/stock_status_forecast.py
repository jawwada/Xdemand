import os
from config import stock_status_settings as cf
from datetime import datetime

from xdemand.pipelines.RDX.stock_status_forecast.stock_status_utils import write_replace_stat_running_stock_forecast, \
    plot_warehouse_stock, merge_shiptment_stocks_forecast, \
    get_forecast_stocks_shipments
from common.logger_ import logger

logger.info("Starting Sotck Status Forecast Pipeline")

logger.info(f"""Merge Stocks, Shipments, and Forecasts, Loop through available stocks, expected data of arrival 
for in transit skus, stocks status and forecasted sales to calculate stock status after forecasted sales""")

forecast_filtered,stocks,shipments=get_forecast_stocks_shipments()
# Merge with stocks DataFrame and calculate stock status
merged_df = merge_shiptment_stocks_forecast(shipments,stocks,forecast_filtered)

logger.info("Write to the database")
# Write to the database
if cf.write_to_db==True:
    print(write_replace_stat_running_stock_forecast(merged_df))

logger.info("Stock Status adjusted Forecast DF example")
logger.info("curnnet date and time is %s" % datetime.now())
print(merged_df.columns)


# Replace 'your_sku' with the actual SKU you want to analyze
if cf.plot==True:
    logger.info("Plot Stock Status after Forecast")
    selected_sku = cf.sku
    plot_warehouse_stock(merged_df, selected_sku)
print("Stock Status Forecasting Done")
