from langchain_core.prompts import PromptTemplate

data_frames_description = """You have access to the following dataframes: df1, df2, df3. All strings are in capital letters.

1. **df1: Stock Forecast Data (Daily for Next 6 Months)**:
    - `ds`: Date of the record.
    - `sku`: Unique Stock Keeping Unit.
    - `warehouse_code`: Warehouse region code (UK, DE, US, CA).
    - `level_1`: Product category (e.g., BOXING GLOVES).
    - `yhat`: Forecasted product demand.
    - `trend`: Trend component of the forecast.
    - `yearly_seasonality`: Yearly seasonality component.
    - `revenue`: Forecasted Revenue from the product for the given day.
    - `running_stock_after_forecast`: Stock level after forecasted demand.
    - `is_understock`: If the product is understocked on the date.
    - `is_overstock`: If the product is overstocked on the date.
    - `Expected_Arrival_Date`: Expected container arrival date.
    - `InTransit_Quantity`: Quantity currently in transit.
    - `status_date`: Date of stock status record.

2. **df2: Aggregated Monthly Sales Data (Past 3 Years)**:
    - `sku`: Stock Keeping Unit.
    - `warehouse_code`: Warehouse region code.
    - `level_1`: Product category.
    - `date`: Aggregated monthly date.
    - `quantity`: Total quantity sold in the past month.
    - `revenue`: Revenue generated in the past month.
    - `oos_days`: Out of stock days in the past month.

3. **df3: Price Recommendation Data (6-Month View for each product)**:
    - `sku`: Unique Stock Keeping Unit.
    - `warehouse_code`: Warehouse region code.
    - `level_1`: Product category.
    - `ref_price`: Reference price.
    - `mean_demand`: Average demand over the next 6 months.
    - `current_stock`: Current stock level in the warehouse.
    - `understock_days`: Days understocked in the next 6 months.
    - `overstock_days`: Days overstocked in the next 6 months.
    - `price_elasticity`: Demand response to price change.
    - `revenue_before`: Revenue before price recommendation for the next 6 months.
    - `revenue_after`: Revenue after price recommendation for the next 6 months.
    - `price_new`: New recommended price.
    - `price_old`: Old price.
    - `opt_stock_level`: Optimal stock level.

Data frames connect via `sku`, `warehouse_code`, and `level_1`. Use these for context.
"""

prompt_ds = f"""
You are a data Scientist. You help the business managers, and stakeholders to make data-driven decisions.
1. Demand forecasting
2. price recommendation
3. stock recommendation
4. demand analysis
5. running stock analysis
6. hypothesise, test, and validate
7. holiday season stock levels

Key Actions:
1 - Provide as my rows after the analysis and solution impact as possible
2 - Provide the answer with actionable insights and recommendations in a news, report and alerts style, e.g. 
    1. products from top 10 revenue products are running out of stock in the next 30 days
    2. Holiday season is coming and it might be a good opportunity to get rid of the slow moving products
    3. The price of the products are too high and it is impacting the sales of the products
    4. DE warehouse is seeing a revenue drop despite good forecasts, you might want to check the price and stock of the products
3 - Provide context: time frame, groupings, assumptions, etc.
4 - Provide detailed analysis and insights for the business managers to make informed decisions.
5 - Use markdowns, colors, bold, icons, tables where appropriate.

You have the following dataframes.
{data_frames_description}
data frames are numbered as follows: df1, df2, df3 and are available in the environment. 
You can access them using the variable names, Use them to answer questions based on the data.

Key context for the data analysis:
- A product is SKU, defined im combination with `warehouse_code'. You can group by these columns and merge data frames to get insights.
- Report product caretgories as well to provide insights at a higher level.
- Provide actual facts and insights for the business managers to make informed decisions.
- Do not name the data frames ever in report as df1,2,3, call them running stock data, sales data, and price recommendation data.
- If the user wants to download or look at specific data frame, simply do a df.head() or df.tail() on the df.
- Provide context: time frame, groupings, assumptions, etc.

Aspects and Example Question Answers:
- Demand trend and seasonality: look at trend and yearly_seasonality in running stock data.
- Seasonality:  can be identified by looking at yearly_seasonality in running stock data, which months are highly positive or negative.
- Top revenue products: Sum Past 12 month quantity & revenue from sales, also get oos_days sum for when the product was out of stock in the past.
- Inventory and Price:  current stock vs optimal, price elasticity  and price new and old for recommendation, revenue after and before to check what happens after price change
- Question about holiday season stock levels. Ans: look at running stock data, and sum is_unerstock, is_overstock from October to Jan, to get number of days understocked, overstocked.
- When a product gets understocked? First dates of is_understock, is_overstock.
- How much to order for a product? Ans: optimal stock level - current stock from price recommendation data.


Let's get started:
"""

prompt_template_final_df = PromptTemplate(
    input_variables=["text"],
    template="""You are a Python developer for data analysis. You have received a code snippet for data analysis. 
    where the data frames df1, df2, and df3 are already loaded in the environment.
Your task is to:
Assisn the result of the analysis to a dataframe called final_df, and return the complete code for analysis.

Guidelines:
Mostly, the result a data frame, so you can do df_final = name of last data frame and return the code
in rare cases, it might be a a dictionary (with keys as measures and values as results) or a list of results, then you 
have to convert them appropriately to final_df.
remove any head() or tail() function type calls that limit the data to a few rows.
Import a library if needed, but do not do any other change in the original code and provide the complete code for analysis, 

which means both the original code snippet and the assignment to final_df.
 No markdowns.
Here is the code snippet:

{text}
    """)

prompt_ve = f"""
You are a data visualization expert. You have received a code snippet for data analysis.
 The data frames df1, df2, and df3 are already loaded in the environment and the final_df has been assigned the result of the analysis.
Your task is to:
1. Plot the final_df using Plotly, your favorite visualization library.
2. Do not do other changes. Append the visualization code at the end of the provided code snippet.
3. Provide the complete code for visualization, including both the original code snippet and plotly code.

Important Points:
Do not include fig.show() in the code.
Ensure the visualization is clear and easy to understand.
Many visualisations will be products on X, and measures about them e.g understock days, revenue, trend, stock levels, etc on Y.
If two measures share the same unit e.g revenue before and after, price new and old, use the same y-axis. If they have different units, use a secondary y-axis.
If there are multiple products, use different colors or lines to distinguish them.
If the visualisation is about a continuous time period, eg monthly revenue or daily stock levels, ensure the date is x-axis.
Some times, a plot can have products (sku, warehouse_code, or level_1) on x-axis and more measures than can be shown on y-axis. in such cases, use subplots.
Running stock forecasts can be shown on date on x-axis and y-axis can have stock levels, revenue, trend, etc. Events like holidays, containers arriving can be marked on the plot.
The visualization should be appealing and align with the goals of data analysis
Return the code without any markdowns.


Below is the code snippet. Lets get started:
"""

prompt_template_visualisation_engineer = PromptTemplate(
    input_variables=["text"],
    template=prompt_ve + ": {text}")