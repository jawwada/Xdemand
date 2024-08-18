# config_constants.py
from sys import platform

CACHE_TYPE = 'filesystem'
CACHE_DIR = 'cache-dataframes'
TIMEOUT = 60 * 60 * 24 * 7  # 24 hours
# Redis connection details
CACHE_REDIS_URL = 'redis://:4Svi3ccc9vDciM6pYqlurHS613IbqZJssAzCaNYSIeU=@xdemand.redis.cache.windows.net:6379'
# Database connection details
import pyodbc

# server = 'tcp:xdemand.database.windows.net'
server = "rdx4sales.database.windows.net"
database = "rdx4cast"
user = "rdxadmin"
password = "13PcPunchBagFullBlack-UK-4FT"
driver = "{ODBC Driver 18 for SQL Server}"
# check if system is darwin or linux
if platform == 'darwin':
    driver = "/opt/homebrew/lib/libmsodbcsql.18.dylib"
    print("OS is Darwin")
connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password}"
cnxn = pyodbc.connect(connection_string)

# Dictionary of valid username-password pairs
VALID_USERNAME_PASSWORD_PAIRS = {
    "nsadiq": "mmxEv2XN",
    "asadiq": "EBZ9KBgK",
    "aarif": "hCTdZj3P",
    "ajawad": "51628",
    "uakram": "fqAJP8ep",
    "sohailibrar": "4Svi3ccc9v",
    "gmabbas": "=9sdf63sd",
    "waqasashraf": "8ad7F632d"
}

'''
query_df_fc_qp = "SELECT * FROM stat_forecast_quantity_revenue ORDER BY ds, sku"

query_sku_sum = f"""SELECT sku, sum(quantity) as quantity, sum(revenue) as revenue FROM agg_daily_sales WHERE sku !='0' and date > DATEADD(year, -1, GETDATE()) group by sku ORDER BY sku """
query_running_stock = f"select * from stat_running_stock_forecast"
query_df_daily_sales = f"""SELECT sku, date, quantity, revenue, price FROM agg_daily_sales WHERE sku !='0' and date > DATEADD(year, -1, GETDATE()) ORDER BY sku,date ; """
'''

# dictionary to jump from radio buttons to sampling rate
sample_rate_dict = {0: "D", 1: "W-Mon", 2: "M"}

# per sampling rate, how many days back we need to go
sample_rate_backdate_dict = {"D": 90, "W-Mon": 365, "M": 365}
