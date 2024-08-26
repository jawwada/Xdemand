import logging

import chromadb
import pandas as pd
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

from xiom_optimized.utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("Xdemand app starting")

# Instantiate CacheManager
cache_manager = CacheManager()


def fetch_ph_data():
    ph_data = pd.read_json(cache_manager.query_ph_data(), orient='split')
    ph_data.fillna('', inplace=True)
    return ph_data


def fetch_daily_sales(ph_data):

    df_daily_sales_da = pd.read_json(cache_manager.query_df_daily_sales(ph_data), convert_dates=['date'],
                                     orient='split')
    df_sales = pd.read_json(cache_manager.query_df_daily_sales_oos(ph_data), convert_dates=['date'], orient='split')
    df_sales.columns = df_sales.columns.str.lower()
    df_sales['date'] = pd.to_datetime(df_sales['date'])
    return df_daily_sales_da, df_sales

def fetch_monthly_sales(ph_data):
    df = pd.read_json(cache_manager.query_df_monthly_sles(ph_data), convert_dates=['ds'], orient='split')
    return df


def fetch_fc_qp(ph_data):
    df_fc_qp = pd.read_json(cache_manager.query_df_fc_qp(ph_data), convert_dates=['ds'], orient='split')
    return df_fc_qp


def fetch_price_recommendations(ph_data):
    df_price_rec = pd.read_json(cache_manager.query_price_recommender(), convert_dates=['ds'], orient='split')
    df_price_rec_summary = pd.read_json(cache_manager.query_price_recommender_summary(ph_data), convert_dates=['ds'],
                                        orient='split')
    return df_price_rec, df_price_rec_summary


def fetch_price_reference(ph_data):
    df_price_reference = pd.read_json(cache_manager.query_price_reference(ph_data), convert_dates=['date'],
                                      orient='split')
    df_price_reference = df_price_reference.groupby(['sku', 'warehouse_code', 'level_1'])['price'].mean().reset_index()
    return df_price_reference


def fetch_price_sensing(ph_data):
    return pd.read_json(cache_manager.query_price_sensing_tab(ph_data), convert_dates=['date'], orient='split')


def fetch_price_regression(ph_data):
    return pd.read_json(cache_manager.query_price_regression_tab(ph_data), convert_dates=['date'], orient='split')


def fetch_sku_summary(df_daily_sales_da):
    return df_daily_sales_da.groupby(['sku'])[['quantity', 'revenue']].sum().reset_index()


def fetch_stockout_past(ph_data):
    return pd.read_json(cache_manager.query_stockout_past(ph_data), convert_dates=['date'], orient='split')


def fetch_running_stock(df_price_reference, ph_data):
    df_running_stock = pd.read_json(cache_manager.query_df_running_stock(ph_data), convert_dates=['date'],
                                    orient='split')
    df_running_stock['ds'] = pd.to_datetime(df_running_stock['ds'])
    df_running_stock = pd.merge(df_running_stock, df_price_reference[['sku', 'warehouse_code', 'level_1', 'price']],
                                how='left',
                                on=['sku', 'warehouse_code', 'level_1'])
    return df_running_stock


def fetch_aggregated_data(df_daily_sales_da, df_sales):
    df_agg_daily_3months = df_daily_sales_da.groupby(['sku', 'warehouse_code', 'level_1', 'date'])[
        ['quantity', 'revenue']].sum().reset_index()
    df_agg_monthly_3years = df_sales.groupby(['sku', 'warehouse_code', 'level_1', pd.Grouper(key='date', freq='M')])[
        ['quantity', 'revenue']].sum().reset_index()
    return df_agg_daily_3months, df_agg_monthly_3years


# fetch product hierarchy data
ph_data = fetch_ph_data()

# fetch daily sales data
df_daily_sales_da, df_sales = fetch_daily_sales(ph_data)

# fetch forecast quantity and price data
df_fc_qp = fetch_fc_qp(ph_data)

# fetch price recommendations
df_price_rec, df_price_rec_summary = fetch_price_recommendations(ph_data)

# fetch price reference, price sensing and price regression data
df_price_reference = fetch_price_reference(ph_data)

# fetch price sensing and price regression data
df_price_sensing_tab = fetch_price_sensing(ph_data)

# fetch price regression data
df_price_regression_tab = fetch_price_regression(ph_data)

# fetch sku summary, stockout past and running stock data
df_sku_sum = fetch_sku_summary(df_daily_sales_da)

# fetch stockout past data
df_stockout_past = fetch_stockout_past(ph_data)

# fetch running stock data
df_running_stock = fetch_running_stock(df_price_reference, ph_data)

# fetch aggregated data

df_agg_monthly_3years = fetch_monthly_sales(ph_data)
chroma_client = chromadb.PersistentClient(path="amazon_reviews")
chroma_collection = chroma_client.get_or_create_collection("amazon_reviews")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(
    client=chroma_client,
    collection_name="amazon_reviews",
    embedding_function=embeddings
)
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(temperature=0.1),
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)
