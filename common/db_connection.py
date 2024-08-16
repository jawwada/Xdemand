import urllib
from sqlalchemy import create_engine
import pandas as pd
import platform

server = "rdx4sales.database.windows.net"
database = "rdx4cast"
user = "rdxadmin"
password = "13PcPunchBagFullBlack-UK-4FT"
driver = "{ODBC Driver 18 for SQL Server}"
if platform.system() == 'Darwin':
    driver = "{/opt/homebrew/lib/libmsodbcsql.18.dylib}"
#connection_string_pyodbc = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password}"
#pyodbc_conn = pyodbc.connect(connection_string_pyodbc)
#cursor = pyodbc_conn.cursor()


params = urllib.parse.quote_plus(
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password}"
)
database='optuna'
optuna_db_params=urllib.parse.quote_plus(
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password}"
)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)

def write_replace_db(df,table_name):
    with engine.connect() as con:
        df.to_sql(table_name, con, if_exists='replace', index=False)
    return True
