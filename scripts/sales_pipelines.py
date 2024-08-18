import logging
import typer
from typing import List

from xdemand.pipelines.sales_pipeline import SalesPipeline

app = typer.Typer(pretty_exceptions_enable=False)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)


@app.command(name='run-sales-pipeline', help='Run the sales forecasting pipeline with specified parameters.')
def main(
        top_n: int = typer.Option(10, help='Top N SKUs to consider.'),
        write_to_db: bool = typer.Option(True, help='Whether to write results to the database.'),
        plot: bool = typer.Option(False, help='Whether to plot results.'),
        min_rows_per_sku: int = typer.Option(365, help='Minimum rows per SKU.'),
        forecast_periods: int = typer.Option(180, help='Number of forecast periods.'),
        forecast_period_freq: str = typer.Option('D', help='Frequency of forecast periods.'),
        target_cols: List[str] = typer.Option(['quantity', 'revenue'], help='Target columns for forecasting.'),
        forecast_tail_periods: int = typer.Option(550, help='Forecast tail periods.'),
        # Price sensing parameters
        price_plot: bool = typer.Option(True, help='Whether to plot price sensing results.'),
        log_normal_regression: bool = typer.Option(True, help='Whether to use log-normal regression.'),
        regressor_lower_bound: int = typer.Option(2, help='Lower bound for the regressor.'),
        regressor_upper_bound: int = typer.Option(2, help='Upper bound for the regressor.'),
        target_lower_bound: int = typer.Option(1, help='Lower bound for the target.'),
        target_upper_bound: int = typer.Option(2, help='Upper bound for the target.'),
        price_target: str = typer.Option('quantity', help='Target for price sensing.'),
        price_write_to_db: bool = typer.Option(True, help='Whether to write price sensing results to the database.'),
        regressor: str = typer.Option('avg_price', help='Regressor to use for price sensing.'),
        days_before: int = typer.Option(365, help='Days before the current date for price sensing.'),
):
    """Main entry point for running the sales pipeline with command line arguments."""
    sales_pipeline = SalesPipeline(
        top_n,
        write_to_db,
        plot,
        min_rows_per_sku,
        forecast_periods,
        forecast_period_freq,
        target_cols,
        forecast_tail_periods,
        price_plot,
        log_normal_regression,
        regressor_lower_bound,
        regressor_upper_bound,
        target_lower_bound,
        target_upper_bound,
        price_target,
        price_write_to_db,
        regressor,
        days_before
    )
    sales_pipeline.run_all_pipelines()


if __name__ == '__main__':
    app()