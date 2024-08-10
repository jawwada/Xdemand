import pandas as pd
from common.db_connection import engine
from sqlalchemy import text
from datetime import datetime
from joblib import Memory
# Create a memory object with a specific cache directory.
memory = Memory("cache_directory", verbose=0)
from common.logger_ import get_logger

@memory.cache
def get_agg_sales(channel='Amazon',region=None,date_from='2021-03-01',date_to=None,freq=None):
    logger = get_logger()
    logger.info(f"Parameter for get agg sales {date_from} date from, {date_to} date to, {freq} freq, {channel} channel,{region} region")

    if date_to is None:
        date_to=datetime.today().date()

    if freq is None:
        df_s = get_sales(channel,region, date_from, date_to)
        return df_s
    else:
        df_ds=get_daily_sales(channel,region,date_from,date_to)
        if freq=='D':
            return df_ds
        else:
            df_ds = df_ds.groupby(['sku', pd.Grouper(key='date', freq=freq)]).sum().reset_index()
    logger.info(f"Created df_ds inside get agg sales, {df_ds.shape[0]} rows and {df_ds.shape[1]} columns")
    logger.info(f"Created df_ds  inside get agg sales, {df_ds['date'].max()} max date and {df_ds['date'].min()} min date")
    return df_ds

@memory.cache
def get_daily_sales(channel='Amazon',
                    region='UK',
                    date_from='2022-01-01',
                    date_to=None):
    logger = get_logger()
    logger.info(f"Parameter for get daily sales {channel} channel, {region} region, {date_from} date from, {date_to} date to")

    if date_to is None:
        date_to=datetime.today().date()
    region_condition = "" if region is None else f"AND region = '{region}'"
    channel_condition = "" if channel is None else f"AND channel = '{channel}'"
    query = f"""
        SELECT
        *
    FROM
        [dbo].[agg_im_sku_daily_sales]
    WHERE
        quantity > 0
        {region_condition}
        {channel_condition}
        AND date >= '{date_from}'
        AND date <= '{date_to}'
        AND sku IN (SELECT im_sku FROM look_product_hierarchy)
    ORDER BY
        [date], sku
    """
    with engine.connect() as con:
        df_ds = pd.read_sql(text(query), con)
    df_ds['date']=pd.to_datetime(df_ds['date'])
    logger.info(f"Created df_ds , {df_ds.shape[0]} rows and {df_ds.shape[1]} columns")
    logger.info(f"Created df_ds , {df_ds['date'].max()} max date and {df_ds['date'].min()} min date")
    return df_ds
def get_sales(channel='Amazon',region=None,  date_from='2022-01-01', date_to=None):
    logger = get_logger()
    logger.info(f"Parameter for get sales {channel} channel, {region} region, {date_from} date from, {date_to} date to")

    if date_to is None:
        date_to = datetime.today().date()

    region_condition = "" if region is None else f"AND asr.region = '{region}'"
    channel_condition = "" if channel is None else f"AND asr.channel = '{channel}'"

    query = f"""
    SELECT 
        asr.CLEAN_DateTime as date,
        lph.im_sku as im_sku, 
        asr.quantity,
        asr.channel,
        asr.region,
        asr.total as revenue,
        asr.quantity 
    FROM 
        stg_tr_amazon_raw as asr
    JOIN 
        look_product_hierarchy as lph ON asr.sku = lph.marketplace_sku
    WHERE 
        asr.[type] = 'Order'
        {region_condition}
        {channel_condition}
        AND asr.CLEAN_DateTime >= '{date_from}'
        AND asr.CLEAN_DateTime <= '{date_to}'  
        AND asr.quantity > 0
        
    ORDER BY 
        asr.[CLEAN_DateTime],
        lph.im_sku
    """
    with engine.connect() as con:
        df = pd.read_sql(text(query), con)

    df['date'] = pd.to_datetime(df['date'])
    logger.info(f"Created df, {df.shape[0]} rows and {df.shape[1]} columns")
    logger.info(f"Created df, {df['date'].max()} max date and {df['date'].min()} min date")
    return df
