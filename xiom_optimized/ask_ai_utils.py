import dash_core_components as dcc
import dash_html_components as html
import dash_table
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from xiom_optimized.data_fetcher import df_agg_monthly_3years as df2
from xiom_optimized.data_fetcher import df_price_rec as df3
from xiom_optimized.data_fetcher import df_running_stock as df1
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
System: You are a data scientist at a retail company. 
Your task is to analyze the company's sales data to provide insights and recommendations. 
Focus on the following areas:
1. Demand forecasting
2. Price recommendation
3. Stock recommendation
4. Demand analysis

You have access to the following dataframes: df1, df2, df3.
{data_frames_description}
df1, df2, df3 are available in the environment. You can access them using the variable names, and answer questions based on the data.
Key context for the data analysis:
- A product is defined by a combination of `sku` and `warehouse_code`. Always consider both columns when answering a question.
- Provide detailed explanations and insights based on the data. 
Example questions to consider:
- What are the top-selling products? Answer with respect to quantity and revenue for past 12 months from sales data.
- What is the optimal stock level for each product? How does it compare to the current stock level? 
Answer with respect to price recommendation and running stock data.
- How does the price recommendation impact revenue? Answer with respect to price recommendation data.
- What is the demand trend for each product? Answer with respect to running stock data.
- Give me a report on a a product . Ans: group by sku, warehouse_code over data frames.
            - Sum Past 12 month quantity from sales data.
            - Sum Past 12 month revenue from sales data.
            - Sum is_understock from running stock data for next 6 months to get number of understock days during next 6 months.
            - Sum of yhat from running stock data for next 6 months to get expected demand.
            - Sum is_overstock from running stock data for next 6 months to get number of overstock days during next 6 months.
- Question about holiday season stock levels. Ans: look at running stock data: sku, warehouse_code combinations from October to Jan.
- What is the optimal price for a product? Ans: look at price recommendation: price_new, price_old, price_elasticity. 

Provide python code used for analysis in the end.
"""

prompt_template_final_df = PromptTemplate(
    input_variables=["text"],
    template="""You are an expert python developer. 
    You are given a python code block from a data scientist.
    The data scientist has written a code snippet to analyze sales data using df1, df2, df3 data frames, which are already loaded in the environment.
    Your task is to transform the code to extract the final data structure from the code and assign it to a data frame called final_df.
    The last data structure in the code is typically the result of the analysis. 
    The data scientist most probably assigned the final data structure to a data frame. In this case assign the last data frame to final_df in the last line.
    But it can be a dictionary of key values (key for measures, values for results) or a list of results.) 
    In this case, you need to convert it to a data frame final_df in the end.
    The final data strcuture can also be a dict of dataframes. In this case, you need to merge the dataframes to get the final_df in the end.
    The data scientist might have cut somewhere data frames using head() or tail() to show the results for only a few rows, remove these function calls.
    Return pure code only without any markdowns with the final data structure transformed to final_df.
    Here is the code snippet:
    {text}
     """)

prompt_ve = f"""
    You are a data visualisation expert. You are given a code snippet of a data analysis. The data frames in the code are already loaded in the environment.
    plot the data using your favourite visualisation library plotly.
    You have access to the following dataframes: df1, df2, df3 to you.
    Append visualisation code at the end of the code snippet and provide the complete code for visualisation including the code snippet and plotly code.
    Respond with only code, do not include any markdown block.
    Do not include fig.show() in the code.
    If the visualisation is a time series plot, make sure to include the date on the x-axis.
    If there are multiple values for y axis, create multiple y axes with different axis limits.
    The visualisation should be appealing and easy to understand for business managers.
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
