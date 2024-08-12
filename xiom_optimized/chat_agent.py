from langchain.agents import AgentType
from langchain.agents import create_structured_chat_agent
from langchain.prompts import PromptTemplate
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain


from xiom_optimized.caching import df_running_stock, \
    df_price_rec_summary, \
    df_agg_monthly_3years

# Define a simple template
prompt_template_code_remover = """
You are a helpful assistant. Remove all code blocks and their contextual information from the following markdown text:
{text}

Provide the left over markdown text. 
"""

prompt_template = PromptTemplate(
    input_variables=["text"],
    template=prompt_template_code_remover
)

prompt_code = """
you are a visualisation expert in plotly dash. You are given a code snippet that reads data from a database and prepares it for visualization.
take the code snippet and create a call back to dynamically update a graph in a dash app.
"""
prompt_ds = f""" 
System: You are a data scientist at a retail company. 
Your task is to analyze the company's sales data to provide insights and recommendations. 
Focus on the following areas:
1. Demand forecasting
2. Price recommendation
3. Stock recommendation
4. Demand analysis

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

df1, df2, df3 are available in the environment. You can access them using the variable names, and answer questions based on the data.
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

Provide python code used for analysis in the end.
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
# Create the agent using create_structured_chat_agent
agent_remove_code_block = LLMChain(
    llm=ChatOpenAI(temperature=0.3, model="gpt-3.5-turbo"),
    prompt=prompt_template)
