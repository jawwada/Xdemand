import logging
import os
import typer
from config import forecast_settings as cf  # Import configuration settings for forecasting
from config import price_sensing_settings as ps_cf  # Import price sensing configuration settings

from xdemand.pipelines.sales_pipeline import SalesPipeline  # Import the SalesPipeline class

# Create a Typer application for command-line interface
app = typer.Typer(pretty_exceptions_enable=False)


logger = logging.getLogger(__name__)  # Set up a logger for this module
# Configure logging to display INFO level messages
logging.basicConfig(level=logging.INFO)

@app.command(name='run-sales-pipeline', help='Run the sales forecasting pipeline with specified parameters.')
def main(
        top_n_skus: int = typer.Option(int(os.getenv('TOP_N_SKUS_XDEMAND', 5)), help='Top N SKUs to consider.')  # Read top_n from environment variable
):
    """Main entry point for running the sales pipeline with command line arguments."""

    # Instantiate the SalesPipeline class with the provided top_n and configuration parameters
    sales_pipeline = SalesPipeline(
        top_n=top_n_skus,  # Set the number of top SKUs to consider
        write_to_db=cf.write_to_db,  # Flag to determine if results should be written to the database
        plot=cf.plot,  # Flag to determine if results should be plotted
        min_rows_per_sku=cf.min_rows_per_sku,  # Minimum number of rows required per SKU for valid forecasting
        forecast_periods=cf.forecast_periods,  # Total number of periods to forecast
        forecast_period_freq=cf.forecast_period_freq,  # Frequency of the forecast periods (e.g., daily)
        target_cols=cf.target_cols,  # List of target columns for forecasting (e.g., quantity, revenue)
        forecast_tail_periods=cf.forecast_tail_periods,  # Number of periods to prepend before the last date in the data

        # Price sensing parameters from the configuration
        price_plot=ps_cf.plot,  # Set price_plot from price sensing config
        price_col=ps_cf.price_col,  # Price column name for price elasticity calculations
        date_col=ps_cf.date_col,  # Date column name for price elasticity calculations
        price_target=ps_cf.target,  # Price target for price sensing
        log_normal_regression=ps_cf.log_normal_regression,  # Set log_normal_regression from price sensing config
        regressor_lower_bound=ps_cf.regressor_lower_bound,  # Set regressor_lower_bound from price sensing config
        regressor_upper_bound=ps_cf.regressor_upper_bound,  # Set regressor_upper_bound from price sensing config
        target_lower_bound=ps_cf.target_lower_bound,  # Set target_lower_bound from price sensing config
        target_upper_bound=ps_cf.target_upper_bound,  # Set target_upper_bound from price sensing config
        price_write_to_db=ps_cf.write_to_db,  # Set price_write_to_db from price sensing config
        days_before=ps_cf.days_before,  # Set days_before from price sensing config

        # Price elasticity parameters from the configuration

        period=ps_cf.price_elasticity.period,  # Period for seasonal decomposition
        model=ps_cf.price_elasticity.model,  # Model type for seasonal decomposition
        remove_months=ps_cf.price_elasticity.remove_months,  # Flag to remove specific months
        remove_months_window=ps_cf.price_elasticity.remove_months_window  # List of months to remove
    )

    # Run the sales forecasting pipeline
    logger.info("Running the sales forecasting pipeline...")
    sales_pipeline.run_prophet_training_pipeline()  # Execute the Prophet training pipeline
    logger.info("Completed the sales forecasting pipeline.")

    # Run the stockout detection pipeline
    logger.info("Running the stockout detection pipeline...")
    sales_pipeline.run_stockout_detection()  # Execute the stockout detection pipeline
    logger.info("Completed the stockout detection pipeline.")
    # Run the price sensing pipeline
    logger.info("Running the price sensing pipeline...")
    sales_pipeline.run_price_sensing()  # Execute the price sensing pipeline
    logger.info("Completed the price sensing pipeline.")

if __name__ == '__main__':
    app()