import logging
import os
import typer

from xdemand.pipelines.RDX.index_reviews.build_chroma import create_amazon_reviews_store, install_argos_packages

# Create a Typer application for command-line interface
app = typer.Typer(pretty_exceptions_enable=False)


logger = logging.getLogger(__name__)  # Set up a logger for this module
# Configure logging to display INFO level messages
logging.basicConfig(level=logging.INFO)

@app.command(name='run-revieww-pipeline', help='Run the sales forecasting pipeline with specified parameters.')
def main():
    # Create Amazon reviews store
    install_argos_packages()
    create_amazon_reviews_store()

if __name__ == '__main__':
    app()