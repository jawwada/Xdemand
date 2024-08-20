# test_tools.py
import pytest
import torch
import math
import logging
import cmdstanpy
import prophet
from prophet import Prophet
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def torch_setup():
    logger.info(f"torch version: {torch.__version__}")
    assert torch.backends.mps.is_available(), "MPS is not available on this MacOS version."
    assert torch.backends.mps.is_built(), "PyTorch was not built with MPS activated."
    return torch

@pytest.fixture(scope="module")
def cmdstanpy_setup():
    logger.info(f"cmdstanpy version: {cmdstanpy.__version__}")
    return cmdstanpy

@pytest.fixture(scope="module")
def prophet_setup():
    logger.info(f"prophet version: {prophet.__version__}")
    return Prophet

def test_torch_mps(torch_setup):
    dtype = torch.float
    device = torch.device("mps")

    # Create random input and output data
    x = torch.linspace(-math.pi, math.pi, 2000, device=device, dtype=dtype)
    y = torch.sin(x)

    # Randomly initialize weights
    a = torch.randn((), device=device, dtype=dtype)
    b = torch.randn((), device=device, dtype=dtype)
    c = torch.randn((), device=device, dtype=dtype)
    d = torch.randn((), device=device, dtype=dtype)

    learning_rate = 1e-6
    for t in range(2000):
        # Forward pass: compute predicted y
        y_pred = a + b * x + c * x ** 2 + d * x ** 3

        # Compute and print loss
        loss = (y_pred - y).pow(2).sum().item()
        if t % 100 == 99:
            logger.info(f"Iteration {t}, Loss: {loss}")

        # Backprop to compute gradients of a, b, c, d with respect to loss
        grad_y_pred = 2.0 * (y_pred - y)
        grad_a = grad_y_pred.sum()
        grad_b = (grad_y_pred * x).sum()
        grad_c = (grad_y_pred * x ** 2).sum()
        grad_d = (grad_y_pred * x ** 3).sum()

        # Update weights using gradient descent
        a -= learning_rate * grad_a
        b -= learning_rate * grad_b
        c -= learning_rate * grad_c
        d -= learning_rate * grad_d

    logger.info(f'Result: y = {a.item()} + {b.item()} x + {c.item()} x^2 + {d.item()} x^3')

def test_cmdstanpy(cmdstanpy_setup):
    # Check if cmdstan is installed
    if not cmdstanpy.cmdstan_path():
        logger.info("CmdStan is not installed. Installing CmdStan...")
        cmdstanpy.install_cmdstan()
    else:
        logger.info("CmdStan is already installed.")

def test_prophet(prophet_setup):
    # Set the start date and number of days
    start_date = datetime(2021, 1, 1)
    num_days = 365

    # Generate dates for the specified number of days
    dates = [start_date + timedelta(days=i) for i in range(num_days)]

    # Generate random values for the time series
    np.random.seed(0)
    values = np.random.randint(0, 100, num_days)

    # Create a DataFrame with the dates and values
    df = pd.DataFrame({'ds': dates, 'y': values})

    # Print the DataFrame
    logger.info(f"DataFrame head:\n{df.head()}")

    # Convert the 'ds' column to datetime format
    df['ds'] = pd.to_datetime(df['ds'])

    # Create a Prophet model
    model = Prophet()

    # Fit the model to the data
    model.fit(df)

    # Generate future dates for forecasting
    future = model.make_future_dataframe(periods=365)

    # Make predictions for the future dates
    forecast = model.predict(future)

    # Print the forecasted values
    logger.info(f"Forecast tail:\n{forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()}")

if __name__ == "__main__":
    pytest.main()