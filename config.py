from dynaconf import Dynaconf

forecast_settings = Dynaconf(
    envvar_prefix="XDEMAND",
    settings_files=['config/sales_forecast_pipeline.yaml'],
    environments=True,
    load_dotenv=True,
)

stock_status_settings = Dynaconf(
    envvar_prefix="XDEMAND",
    settings_files=['config/stock_status_forecast.yaml'],
    environments=True,
    load_dotenv=True,
)
price_sensing_settings = Dynaconf(
    envvar_prefix="XDEMAND",
    settings_files=['config/price_sensing_direct.yaml'],
    environments=True,
    load_dotenv=True,
)
price_recommendation_settings = Dynaconf(
    envvar_prefix="XDEMAND",
    settings_files=['config/price_recommender.yaml'],
    environments=True,
    load_dotenv=True,
)
