from common.db_connection import engine
from common.logger_ import logger
from config import price_recommendation_settings as pr_cf
from xdemand.pipelines.RDX.price_recommender.price_optimizer import price_optimizer
from xdemand.pipelines.RDX.price_recommender.pr_utils import get_data_price_recommender
from xdemand.pipelines.RDX.stock_status_forecast.stock_status_utils import get_forecast_stocks_shipments
from xdemand.pipelines.RDX.stock_status_forecast.stock_status_utils import merge_shiptment_stocks_forecast
from xdemand.pipelines.RDX.stock_status_forecast.stock_status_utils import write_replace_stat_running_stock_forecast


def run_stock_status_forecast():
    logger.info("Starting Stock Status Forecast Pipeline")

    # Get forecast, stocks and shipments
    forecast_filtered, stocks, shipments = get_forecast_stocks_shipments()
    # Merge with stocks DataFrame and calculate stock status
    merged_df = merge_shiptment_stocks_forecast(shipments, stocks, forecast_filtered)

    logger.info("Write to the database")
    # Write to the database
    return_status = write_replace_stat_running_stock_forecast(merged_df)
    logger.info(f"Saved stock status to database with status {return_status}")
    print("Stock Status Forecasting Tables Done")

def run_price_recommender():
    n_trials = pr_cf.n_trials

    # Get the data
    df_price_recommender= get_data_price_recommender()

    # Clip the price_elasticity to -1 and -5
    df_price_recommender['price_elasticity'] = df_price_recommender['price_elasticity'].clip(-5, -1)

    # Run the Optuna trials
    price_adjustments, df_sku_warehouse_pr = price_optimizer(df_price_recommender, pr_cf)

    price_adjustments.reset_index().to_sql('stat_price_recommender',con=engine,if_exists='replace')
    df_sku_warehouse_pr.reset_index().to_sql('stat_price_recommender_summary',con=engine,if_exists='replace')

    print("Price Recommendation Tables Done")
    return

if __name__ == '__main__':
    logger.info("Starting RDX Stock and PR Pipeline")
    run_stock_status_forecast()
    run_price_recommender()