import warnings
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns  # data visualization library
from tqdm import tqdm

warnings.filterwarnings('ignore')


def get_daily_sales(engine) -> pd.DataFrame:
    """
    Fetch daily sales data from the database.

    Args:
        engine: SQLAlchemy engine object for database connection.

    Returns:
        pd.DataFrame: DataFrame containing daily sales data.
    """
    query = """
    SELECT * FROM agg_im_sku_daily_sales 
    WHERE sku IN (SELECT DISTINCT sku FROM look_product_hierarchy) 
    AND date > DATEADD(year, -3, GETDATE()) 
    ORDER BY sku, region, date;
    """
    with engine.connect() as con:
        daily_sales = pd.read_sql_query(query, con)
    daily_sales['date'] = pd.to_datetime(pd.to_datetime(daily_sales['date']).dt.date)
    daily_sales['sku'] = daily_sales['sku'].str.replace('^M-', '', regex=True)
    daily_sales['year'] = daily_sales['date'].dt.year
    daily_sales['month'] = daily_sales['date'].dt.month
    daily_sales['year_month'] = daily_sales['date'].dt.to_period('M')
    daily_sales['revenue'] = daily_sales['revenue'].astype(float)
    daily_sales['warehouse_code'] = daily_sales['region'].str[0:2]
    return daily_sales

def fill_missing_dates(df_sku: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing dates in the DataFrame for each SKU.

    Args:
        df_sku: DataFrame containing SKU data with missing dates.

    Returns:
        pd.DataFrame: DataFrame with missing dates filled.
    """
    min_date = df_sku['date'].min()
    max_date = df_sku['date'].max()
    idx = pd.date_range(min_date, max_date)
    df_sku = df_sku.set_index('date').reindex(idx).rename_axis('date').reset_index()
    df_sku['sku'] = df_sku['sku'].fillna(method='ffill')
    df_sku['warehouse_code'] = df_sku['warehouse_code'].fillna(method='ffill')
    df_sku['channel'] = df_sku['channel'].fillna(method='ffill')
    df_sku['quantity'] = df_sku['quantity'].fillna(0)
    return df_sku


def get_total_days_dict(df_filled: pd.DataFrame) -> dict:
    """
    Calculate the total number of days for each SKU and warehouse combination.

    Args:
        df_filled: DataFrame with filled dates.

    Returns:
        dict: Dictionary with SKU and warehouse as keys and total days as values.
    """
    total_days = df_filled.groupby(['sku', 'warehouse_code'])['date'].agg(['min', 'max']).reset_index()
    total_days['total_days'] = (total_days['max'] - total_days['min']).dt.days
    total_days_dict = {(row['sku'], row['warehouse_code']): row['total_days'] for _, row in total_days.iterrows()}
    return total_days_dict


def process_sku_warehouse_combinations(grid_df: pd.DataFrame, total_days_dict: dict) -> pd.DataFrame:
    """
    Process each SKU and warehouse combination to calculate gaps, expected sales years, and sale probabilities.

    Args:
        grid_df: DataFrame with filled dates and sales data.
        total_days_dict: Dictionary with SKU and warehouse as keys and total days as values.

    Returns:
        pd.DataFrame: DataFrame with calculated gaps, expected sales years, and sale probabilities.
    """
    s_list, e_list, p_list = [], [], []

    for prod_id, dfx in tqdm(grid_df.groupby(["sku", 'warehouse_code'])):
        sales_gaps = dfx.loc[:, 'gaps']
        zero_days = sum(sales_gaps)
        p = zero_days / total_days_dict[(prod_id[0], prod_id[1])]

        accum_add_prod = np.frompyfunc(lambda x, y: int((x + y) * y), 2, 1)
        sales_gaps[:] = accum_add_prod.accumulate(dfx["gaps"], dtype=np.object).astype(int)
        sales_gaps[sales_gaps < sales_gaps.shift(-1)] = np.NaN
        sales_gaps = sales_gaps.fillna(method="bfill").fillna(method='ffill')
        s_list += [sales_gaps]

        gap_length = sales_gaps.unique()
        d = {length: ((1 - p ** length) / (p ** length * (1 - p))) / 365 for length in gap_length}
        sales_E_years = sales_gaps.map(d)

        p1 = 0
        while p1 < p:
            if p1 != 0:
                p = p1
            gap_days = sum(sales_E_years > 100)
            p1 = (zero_days - gap_days + 0.0001) / (total_days_dict[prod_id] - gap_days)
            d = {length: ((1 - p1 ** length) / (p1 ** length * (1 - p1))) / 365 for length in gap_length}
            sales_E_years = sales_gaps.map(d)

        e_list += [sales_E_years]
        p_list += [pd.Series(p, index=sales_gaps.index)]

    grid_df['gap_days'] = pd.concat(s_list)
    grid_df['gap_e'] = pd.concat(e_list)
    grid_df['sale_prob'] = pd.concat(p_list)
    grid_df['gap_e_log10'] = np.log10((grid_df['gap_e'].values + 1))
    grid_df.loc[grid_df['gap_e_log10'] > 2, 'gap_e_log10'] = 2

    return grid_df


def visualize_stockout(grid_df: pd.DataFrame) -> None:
    """
    Visualize stockout data using a heatmap.

    Args:
        grid_df: DataFrame with stockout data.
    """
    grid_df['dept_id'] = grid_df['sku'].str.split('-').str.get(0)
    grid_df['item_id'] = grid_df['sku'].str.split('-').str.get(1)
    np.random.seed(19)
    depts = list(grid_df.dept_id.unique())
    prod_list = []
    for d in depts:
        prod_by_dept = grid_df['item_id'][grid_df.dept_id == d].unique()
        prod_list += list(np.random.choice(prod_by_dept, 5))

    m = grid_df.item_id.isin(prod_list)
    viz_df = grid_df[m]
    one_year_ago = datetime.today() - timedelta(days=365)
    viz_df = viz_df[viz_df['date'] > one_year_ago]
    max_date = max(grid_df['date'])
    viz_df['last_data_seen'] = max_date
    viz_df = viz_df.replace([np.inf, -np.inf], 0)
    viz_df['sku_warehouse'] = viz_df['sku'] + '-' + viz_df['warehouse_code']
    v_df = viz_df.pivot(index='date', columns='sku_warehouse', values='gap_e_log10')
    v_df = v_df.reindex(sorted(v_df.columns), axis=1)
    f, ax = plt.subplots(figsize=(40, 20))
    temp = sns.heatmap(v_df, cmap='Reds')
    plt.savefig('stockout.png')
    plt.show()


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess the DataFrame to replace inf values with None.

    Args:
        df: DataFrame containing the data to be inserted into the database.

    Returns:
        pd.DataFrame: DataFrame with inf values replaced by None.
    """
    df.replace([np.inf, -np.inf], None, inplace=True)
    return df
