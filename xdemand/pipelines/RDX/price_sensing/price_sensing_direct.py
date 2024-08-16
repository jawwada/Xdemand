import sys

from matplotlib import pyplot as plt

from common.db_connection import write_replace_db
from common.logger_ import logger
from config import price_sensing_settings as cf
from xdemand.pipelines.RDX.price_sensing.elasticity_log_ST_adjusted import get_price_elasticity
from xdemand.pipelines.RDX.price_sensing.ps_utils import daily_sales_price_sensing_transform
from xdemand.pipelines.RDX.price_sensing.ps_utils import std_price_regression

logger.info("Starting test model")

sys.path.append('/opt/homebrew/lib')

""" *************** 2. Create ABT *************** """
df_dsa = daily_sales_price_sensing_transform()
# log parameters
logger.info(f"Parameters for regression, {cf.top_n} top n, {cf.regressor} regressors,  {cf.target} target")
max_date = max(df_dsa['date'])
df_dsa['date_part'] = df_dsa['date'].dt.date
# log min and max dates
logger.info(f"Max date {max_date} and min date {df_dsa['date'].min()}")

""" *************** 3. Run regression *************** """
reg_coef_df = get_price_elasticity(df_dsa)
logger.info(f"reg_coef_df.head() {reg_coef_df.head()}")
log_normal_regressions = std_price_regression(df_dsa)

""" *************** 4. Save/Plot regression results *************** """
# Write regression coefficients and results to the database
if cf.write_to_db:
    write_replace_db(reg_coef_df, f'stat_regression_coeff_{cf.regressor}_{cf.target}')
    write_replace_db(log_normal_regressions, f'stat_regression_{cf.regressor}_{cf.target}')
    logger.info(f"Saved regression results to database for regressor {cf.regressor} and target {cf.target}")

if cf.plot:
    df_dsa.plot.scatter(x='avg_price', y='quantity')
    plt.show()
