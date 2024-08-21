from common.db_connection import engine
from config import price_recommendation_settings as cf
from xdemand.pipelines.RDX.price_recommender.pr_utils import get_data_price_recommender
from xdemand.pipelines.RDX.price_recommender.price_optimizer import price_optimizer

# Check if running under PyCharm debugger
# Get the data
df_price_recommender = get_data_price_recommender()
# If running in debug mode, only run for one SKU
df_price_recommender = df_price_recommender[df_price_recommender['sku'].isin(["HYP-IBB-M"])]

# Clip the price_elasticity to -1 and -5
df_price_recommender['price_elasticity'] = df_price_recommender['price_elasticity'].clip(-5, -1)
# Run the Optuna trials
price_adjustments, df_sku_warehouse_pr = price_optimizer(df_price_recommender, cf)
# Save the results to the database
try:
    price_adjustments.to_sql('stat_price_recommender', con=engine, if_exists='replace')
    df_sku_warehouse_pr.to_sql('stat_price_recommender_summary', con=engine, if_exists='replace')
except Exception as e:
    with engine.connect() as con:
        price_adjustments.to_sql('stat_price_recommender', con=con, if_exists='replace')
        df_sku_warehouse_pr.to_sql('stat_price_recommender_summary', con=con, if_exists='replace')

print("Price Recommendation Summary Done")
