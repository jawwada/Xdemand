import sys
from xdemand.pipelines.RDX.price_recommender.pr_utils import get_data_price_recommender
from xdemand.pipelines.RDX.price_recommender.optuna_trials import optune_run_trials
from common.db_connection import engine
from config import price_recommendation_settings as cf
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

n_trials = cf.n_trials

# Check if running under PyCharm debugger
def is_debugger_active():
    gettrace = getattr(sys, 'gettrace', None)
    if gettrace is None:
        return False
    else:
        return gettrace() is not None

debug_mode = is_debugger_active()

# Get the data
df_price_recommender, df_sku_info = get_data_price_recommender()

# If running in debug mode, only run for one SKU
if debug_mode:
    df_price_recommender = df_price_recommender[df_price_recommender['sku'].isin(["HYP-IBB-M"])]
    df_sku_info = df_sku_info[df_sku_info['sku'].isin(["HYP-IBB-M"])]

# Clip the price_elasticity to -1 and -5
df_sku_info['price_elasticity'] = df_sku_info['price_elasticity'].clip(-5, -1)
df_price_recommender['price_elasticity'] = df_price_recommender['price_elasticity'].clip(-5, -1)


# Run the Optuna trials
all_adjustments, df_new = optune_run_trials(df_price_recommender,
                                            df_sku_info.set_index(['sku', 'warehouse_code']),
                                            n_trials)

# Save the results to the database
try:
    all_adjustments.reset_index().to_sql('stat_price_recommender',
                                         con=engine,
                                         if_exists='replace')

    df_new.reset_index().to_sql('stat_price_recommender_summary',
                                con=engine,
                                if_exists='replace')
except Exception as e:
    with engine.connect() as con:
        all_adjustments.reset_index().to_sql('stat_price_recommender',
                                             con=con,
                                             if_exists='replace')

        df_new.reset_index().to_sql('stat_price_recommender_summary',
                                    con=con,
                                    if_exists='replace')

print("Price Recommendation Summary Done")