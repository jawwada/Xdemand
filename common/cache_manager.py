from functools import wraps
from pathlib import Path
import pandas as pd
from flask_caching import Cache as FlaskCache
from diskcache import Cache as DiskCache
import pickle

from common.local_constants import region_warehouse_codes
from common.logger_ import get_logger
from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.config_constants import CACHE_REDIS_URL, CACHE_TYPE, TIMEOUT
from get_db_tables import (
    query_ph_data, query_df_daily_sales_oos, query_df_daily_sales, query_df_fc_qp,
    query_df_running_stock, query_stockout_past, query_price_sensing_tab, query_price_regression_tab,
    query_price_reference, query_price_recommender_summary, query_price_recommender
)

logger = get_logger()
logger.info("Xdemand app starting")

class CacheManager:
    def __init__(self, cache_type='flask'):
        self.cache_type = cache_type
        if cache_type == 'flask':
            cache_dir = 'cache_flask'
            self.cache = FlaskCache(app.server, config={
                'CACHE_TYPE': 'redis' if CACHE_TYPE == 'redis' else 'filesystem',
                'CACHE_REDIS_URL': CACHE_REDIS_URL,
                'CACHE_DIR': cache_dir,
                'CACHE_DEFAULT_TIMEOUT': TIMEOUT
            })
            if CACHE_TYPE == 'filesystem':
                Path(cache_dir).mkdir(exist_ok=True)
        elif cache_type == 'disk':
            cache_dir = 'cache_disk'
            self.cache = DiskCache(cache_dir)
            Path(cache_dir).mkdir(exist_ok=True)
        elif cache_type == 'pickle':
            cache_dir = 'cache_pickle'
            self.cache = {}
            Path(cache_dir).mkdir(exist_ok=True)
        else:
            raise ValueError(f'CACHE_TYPE {cache_type} not supported')

    def cache_decorator(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}_{args}_{kwargs}"
            if self.cache_type == 'flask':
                return self.cache.memoize(timeout=TIMEOUT)(func)(*args, **kwargs)
            elif self.cache_type == 'disk':
                if key in self.cache:
                    return self.cache[key]
                result = func(*args, **kwargs)
                self.cache.set(key, result, expire=TIMEOUT)
                return result
            elif self.cache_type == 'pickle':
                if key in self.cache:
                    return pickle.loads(self.cache[key])
                result = func(*args, **kwargs)
                self.cache[key] = pickle.dumps(result)
                return result
        return wrapper

    @property
    def cache_decorator(self):
        return self.cache_decorator

    @cache_decorator
    def query_ph_data(self):
        return query_ph_data()

    @cache_decorator
    def query_df_daily_sales_oos(self):
        return query_df_daily_sales_oos()

    @cache_decorator
    def query_df_daily_sales(self):
        return query_df_daily_sales()

    @cache_decorator
    def query_df_fc_qp(self):
        return query_df_fc_qp()

    @cache_decorator
    def query_df_running_stock(self):
        return query_df_running_stock()

    @cache_decorator
    def query_stockout_past(self):
        return query_stockout_past()

    @cache_decorator
    def query_price_sensing_tab(self):
        return query_price_sensing_tab()

    def query_price_regression_tab(self):
        return query_price_regression_tab()

    @cache_decorator
    def query_price_reference(self):
        return query_price_reference()

    @cache_decorator
    def query_price_recommender_summary(self):
        return query_price_recommender_summary()

    @cache_decorator
    def query_price_recommender(self):
        return query_price_recommender()