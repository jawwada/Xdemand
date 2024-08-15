import dash_core_components as dcc
import dash_html_components as html
import dash_table
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from xiom_optimized.utils.data_fetcher import df_agg_monthly_3years as df2
from xiom_optimized.utils.data_fetcher import df_price_rec as df3
from xiom_optimized.utils.data_fetcher import df_running_stock as df1
from langchain_openai import ChatOpenAI


data_frames_description = """You have access to the following dataframes: df1, df2, df3.
1. **df1: running stock data **:
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

2. **df2: 3 years of monthly aggregated sales data**:
    - `sku`: 
    - `warehouse_code`:
    - `date`: The date of the record.
    - `quantity`: Total quantity sold.
    - `revenue`: Revenue generated.

3. **df3: price recommendation data**:
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
"""

# Define a prompt for a data scientist
prompt_ds = f""" 
System: You are a data scientist at a retail company. Your task is to analyze the company's sales data to provide insights and recommendations. Focus on the following areas:
Demand forecasting
Price recommendation
3. Stock recommendation
4. Demand analysis
You have access to the following dataframes: df1, df2, df3. These data frames are available in the environment and can be accessed using their variable names.
Their descriptions are as follows:
{data_frames_description}
Key context for the data analysis:
A product is defined by a combination of sku and warehouse_code. Always consider both columns when answering a question.
Provide detailed explanations and insights based on the data.
Example questions to consider:
What are the top-selling products? Answer with respect to quantity and revenue for the past 12 months from sales data.
What is the optimal stock level for each product? How does it compare to the current stock level? Answer with respect to price recommendation and running stock data.
How does the price recommendation impact revenue? Answer with respect to price recommendation data.
What is the demand trend for each product? Answer with respect to running stock data.
Give me a report on a product. Group by sku, warehouse_code over data frames:
Sum past 12 months' quantity and revenue from sales data.
Sum is_understock, is_overstock from running stock data for the next 6 months to get the number of under or overstock days during the next 6 months.
Sum yhat from running stock data for the next 6 months to get expected demand.
Question about holiday season stock levels. Look at running stock data: sku, warehouse_code combinations from October to January in the future.
What is the optimal price for a product? Look at price recommendation: price_new, price_old, price_elasticity.
sort the results in the order of their impact on revenue.
Create business impact with insightful analysis and recommendations in makrdown format.
"""

prompt_template_final_df = PromptTemplate(
    input_variables=["text"],
    template="""You are a Python developer. You have received a code snippet from a data scientist who is analyzing sales data using data frames df1, df2, and df3, which are already loaded in the environment.
Your task is to:
1. Identify the final data structure in the code, which is typically the result of the analysis.
2. Assign this final data structure to a data frame called final_df.
Consider the following scenarios:
1. If the final data structure is a data frame, assign it directly to final_df.
2. If the final data structure is a dictionary (with keys as measures and values as results) or a list of results, convert it to a data frame and assign it to final_df.
3. If the final data structure is a dictionary of data frames, merge these data frames to create final_df.
Additionally, remove any head() or tail() function calls that limit the data to a few rows.

Finally, Provide the complete code for analysis, including both the original code snippet and the assignment to final_df. No markdowns are needed.
Here is the code snippet:
     """)

prompt_ve = f"""
    You are a data visualization expert. You have received a code snippet for data analysis. The data frames df1, df2, and df3 are already loaded in the environment.
Your task is to:
Plot the data using Plotly, your favorite visualization library.
2. Append the visualization code at the end of the provided code snippet.
3. Provide the complete code for visualization, including both the original code snippet and the Plotly code.
Consider the following:
Do not include fig.show() in the code.
If the visualization is a time series plot, ensure the date is on the x-axis.
If there are multiple values for the y-axis, create multiple y-axes with different axis limits.
The visualization should be appealing and easy to understand for business managers.
    """

prompt_template_visualisation_engineer = PromptTemplate(
    input_variables=["text"],
    template=prompt_ve + ": {text}")

agent_visualisation = LLMChain(
    llm=ChatOpenAI(temperature=0.2, model="gpt-4o-mini"),
    prompt=prompt_template_visualisation_engineer)

agent_data_table = LLMChain(
    llm=ChatOpenAI(temperature=0.2, model="gpt-4o-mini"),
    prompt=prompt_template_final_df)


def get_fig_from_code(code):
    local_variables = {}
    global_variables = {'df1': df1, 'df2': df2, 'df3': df3}
    exec(code, global_variables, local_variables)
    return local_variables['fig']


def get_final_df_from_code(code):
    local_variables = {}
    global_variables = {'df1': df1, 'df2': df2, 'df3': df3}
    exec(code, global_variables, local_variables)
    return local_variables['final_df']


def generate_table(response_code):
    print(response_code)
    try:
        final_df = get_final_df_from_code(response_code)
        table = html.Div([
            html.Button("Download Full Excel", id="download-button-final-df",
                        className='btn btn-primary',
                        style={'display': 'flex', 'align-items': 'flex-start',
                               'justify-content': 'flex-end'}),
            dcc.Download(id="download-dataframe-xlsx"),
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in final_df.columns],
                data=final_df.head(100).to_dict('records'),
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'},
            )
        ])
        return table
    except Exception as e:
        print(f"Error in generate_table: {str(e)}")
        return html.Div("Error generating table")


def generate_graph(response_code):
    print(response_code)
    try:
        plotly_agent_response = agent_visualisation.invoke(response_code)
        fig = get_fig_from_code(plotly_agent_response["text"])
        return dcc.Graph(figure=fig)
    except Exception as e:
        print(e)
        return html.Div("Error generating graph")
