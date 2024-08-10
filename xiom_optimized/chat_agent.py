import os

from dash import dcc
from xiom_optimized.caching import df_fc_qp,  \
    df_running_stock, \
    df_price_rec_summary, \
    df_price_sensing_tab,  \
    ph_data,  \
    df_price_reference, \
    df_agg_monthly_3years



from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

prompt = f""" 
You are a data scientist at a retail company. 
Your task is to analyze the company's sales data to provide insights and recommendations. 
Focus on the following areas:
1. Demand forecasting
2. Price recommendation
3. Stock recommendation
4. Demand analysis

You have access to the following dataframes:

1. **df_running_stock**:
    - `ds`: The date of the record.
    - `sku`: Stock Keeping Unit, a unique identifier for each product.
    - `warehouse_code`: Code representing the warehouse region where the product is stored. [UK,DE,US,CA]
    - `yhat`: Forecasted quantity for the product demand.
    - `trend`: The trend component of the forecast.
    - `yearly_seasonality`: The yearly seasonality component of the forecast.
    - `revenue`: Revenue generated from the product.
    - `running_stock_after_forecast`: The stock level after considering the forecasted demand.
    - `is_understock`: Indicator if the product is understocked on the date.
    - `is_overstock`: Indicator if the product is overstocked on the date.
    - `Expected_Arrival_Date`: The expected date of arrival for new stock.
    - `InTransit_Quantity`: Quantity of the product that is currently in transit.
    - `status_date`: The date when the status was recorded.

2. **df_agg_monthly_3years**:
    - `sku`: Stock Keeping Unit, a unique identifier for each product.
    - `warehouse_code`: Code representing the warehouse where the product is stored.
    - `date`: The date of the record.
    - `quantity`: Total quantity sold.
    - `revenue`: Revenue generated.

3. **df_price_rec_summary**:
    - `sku`: Stock Keeping Unit, a unique identifier for each product.
    - `warehouse_code`: Code representing the warehouse where the product is stored.
    - `yhat`: Forecasted quantity for the product demand.
    - `ref_price`: Reference price for the product.
    - `price_elasticity`: Measure of how the quantity demanded of a product responds to a change in price.
    - `opt_stock_level`: Optimal stock level for the product.
    - `revenue_before`: Revenue generated before the price recommendation.
    - `revenue_after`: Revenue generated after the price recommendation.
    - `price_new`: New recommended price for the product.
    - `price_old`: Old price of the product.
    - `s_opt`: Optimal stock level after the price recommendation.
    - `avg_yhat`: Average forecasted quantity for the product demand.
data frames are numbered as follows: df1, df2, df3 and are available in the environment.
Key context for the data analysis:
- A product is defined by a combination of `sku` and `warehouse_code`. Always consider both columns when analyzing a product.
- Provide detailed explanations and insights based on the data.


Let's get started!

"""

# create agent
dataframes = [
    df_running_stock,  # df1
    df_agg_monthly_3years,  # df2
    df_price_rec_summary,  # df3


]

agent_running_stock = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0.1, model="gpt-4-1106-preview"),
    dataframes,
    verbose=True,
    agent_type=AgentType.OPENAI_FUNCTIONS,
    number_of_head_rows=20,
    allow_dangerous_code=True
)