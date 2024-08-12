import os

from dash import dcc
from xiom_optimized.caching import df_fc_qp, \
    df_running_stock, \
    df_price_rec_summary, \
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

Your task has two parts:
# Part 1:
You have access to the following dataframes: df1, df2, df3.

1. **df1:df_running_stock**:
    - `ds`: The date of the record.
    - `sku`: Stock Keeping Unit, a unique identifier .
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

2. **df2:df_agg_monthly_3years**:
    - `sku`: 
    - `warehouse_code`:
    - `date`: The date of the record.
    - `quantity`: Total quantity sold.
    - `revenue`: Revenue generated.

3. **df3:df_price_rec_summary**:
    - `sku`: .
    - `warehouse_code`:.
    - `yhat`: average Forecasted quantity for the product demand.
    - `ref_price`: Reference price for the product.
    - `price_elasticity`: Measure of how the quantity demanded of a product responds to a change in price.
    - `opt_stock_level`: Optimal stock level for the product.
    - `revenue_before`: Revenue generated before the price recommendation.
    - `revenue_after`: Revenue generated after the price recommendation.
    - `price_new`: New recommended price for the product.
    - `price_old`: Old price of the product.
    - `s_opt`: Optimal stock level after the price recommendation.
    - `avg_yhat`: Average forecasted quantity for the product demand.

df1, df2, df3 and are available in the environment. You can access them using the variable names,
and answer questions based on the data.
Key context for the data analysis:
- A product is defined by a combination of `sku` and `warehouse_code`. Always consider both columns when answering a question.
- Provide detailed explanations and insights based on the data.

Example questions to consider:
- What are the top-selling products? Answer with respect to quantity and revenue for past 12 months from df_agg_monthly_3years.
- What is the optimal stock level for each product? How does it compare to the current stock level? Answer with respect to df_price_rec_summary and df_running_stock.
- How does the price recommendation impact revenue? Answer with respect to df_price_rec_summary.
- What is the demand trend for each product? Answer with respect to df_running_stock.
- Give me a report on a a product . Ans: group by sku, warehouse_code over data frames.
            - Sum Past 12 month quantity from df_agg_monthly_3years
            - Sum Past 12 month revenue from df_agg_monthly_3years
            - Sum is_understock from df_running_stock for next 6 months to get number of understock days during next 6 months.
            - Sum of yhat from df_running_stock for next 6 months to get expected demand.
            - Sum is_overstock from df_running_stock for next 6 months to get number of overstock days during next 6 months.

- Question about holiday season stock levels. Ans: look at df_running_stock sku, warehouse_code combinations from October to Jan.
- What is the optimal price for a product? Ans: look at df_price_rec_summary: price_new, price_old, price_elasticity.
# Part 2:
At the very end of your response, Provide in only one python code block in ```python``` that does the following. 
1. Defines a full function performing the analysis from question called analyse_data with signature: 
analyse_data(df1, df2, df3):
2. Defines a dash plotly callback function that calls analyse_data and returns the results in a dash table or plotly graph.
The purpose of this code block is to demonstrate how the analysis can be automated in a dashboard. 
Do not define a new app or layout, just the callback function. 
Text of your response should not include any context for the code block. No heading, explanation or comments.
"""
# create agent
dataframes = [
    df_running_stock,  # df1
    df_agg_monthly_3years,  # df2
    df_price_rec_summary  # df3
]
agent_running_stock = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0.3, model="gpt-4o-mini"),
    dataframes,
    verbose=True,
    agent_type=AgentType.OPENAI_FUNCTIONS,
    number_of_head_rows=20,
    allow_dangerous_code=True
)