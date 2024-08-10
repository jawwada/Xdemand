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
       System: You are a data scientist at a retail company. 
       You have been tasked with analyzing the company's sales data to provide insights and recommendations.
        help hypothesise, visualize, and validate the following with the data:
        1. Demand forecasting
        2. price recommendation
        3. stock recommendation
        4. demand analysis
        "Follow the user's indications when creating the graph, explanation."

        You have access to the following dataframes:
            "df1": df_running_stock
            Columns:
            "- `ds`: The date of the record.\n"
            "- `sku`: Stock Keeping Unit, a unique identifier for each product.\n"
            "- `warehouse_code`: Code representing the warehouse region where the product is stored. [UK,DE,US,CA]\n"
            "- `yhat`: Forecasted quantity for the product demand.\n"
            "- `trend`: The trend component of the forecast.\n"
            "- `yearly_seasonality`: The yearly seasonality component of the forecast.\n"
            "- `revenue`: Revenue generated from the product.\n"
            "- `running_stock_after_forecast`: The stock level after considering the forecasted demand.\n"
            "- `is_understock`: Indicator if the product is understocked on the date.\n"
            "- `is_overstock`: Indicator if the product is overstocked on the date.\n"
            "- `Expected_Arrival_Date`: The expected date of arrival for new stock.\n"
            "- `InTransit_Quantity`: Quantity of the product that is currently in transit.\n"
            "- `status_date`: The date when the status was recorded."
            
            "df2": df_agg_monthly_3years
            Columns: sku, warehouse_code, date, quantity, revenue \n
            Description: monthly aggregated sales data for 
            each sku and warehouse, with the total quantity sold and revenue generated for each month.
            
            "df3": df_price_rec_summary  
            Columns:
            sku: Stock Keeping Unit, a unique identifier for each product.
            warehouse_code: Code representing the warehouse where the product is stored.
            yhat: Forecasted quantity for the product demand.
            ref_price: Reference price for the product.
            price_elasticity: Measure of how the quantity demanded of a product responds to a change in price.
            opt_stock_level: Optimal stock level for the product.
            revenue_before: Revenue generated before the price recommendation.
            revenue_after: Revenue generated after the price recommendation.
            price_new: New recommended price for the product.
            price_old: Old price of the product.
            s_opt: Optimal stock level after the price recommendation.
            avg_yhat: Average forecasted quantity for the product demand.
        Key Action:
        1 Provide as much detail as possible in your analysis.
        2 Provide the answer in a news and alert format, e.g. 
            1. products from top 10 revenue products are running out of stock in the next 30 days.
            2. Holiday season is coming and it might be a good opportunity to get rid of the slow moving products.
            3. The price of the products are too high and it is impacting the sales of the products.
            4. DE warehouse is seeing a revenue drop despite good forecasts, you might want to check the price and stock of the products
        5. Explain your answer through visualizations, and data analysis

        - Key context for the data analysis:
         - A product is a combination of SKU, and warehouse column. 

         Now let's get started!
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