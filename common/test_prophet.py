
def check_cmdstanpy():
    logger.info(f"cmdstanpy version: {cmdstanpy.__version__}")
    if not cmdstanpy.cmdstan_path():
        logger.info("CmdStan is not installed. Installing CmdStan...")
        cmdstanpy.install_cmdstan()
    else:
        logger.info("CmdStan is already installed.")


def check_prophet():
    logger.info(f"prophet version: {prophet.__version__}")

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

    logger.info(f"Forecast tail:\n{forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()}")


if __name__ == "__main__":
    check_cmdstanpy()
    check_prophet()