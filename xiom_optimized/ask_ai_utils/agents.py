from langchain.agents.agent_types import AgentType
from langchain.chains import LLMChain
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

from xiom_optimized.ask_ai_utils.prompts import prompt_template_final_df
from xiom_optimized.ask_ai_utils.prompts import prompt_template_visualisation_engineer
from xiom_optimized.utils.data_fetcher import df_agg_monthly_3years
from xiom_optimized.utils.data_fetcher import df_price_rec_summary
from xiom_optimized.utils.data_fetcher import df_running_stock

# create agent
dataframes = [
    df_running_stock,  # df1
    df_agg_monthly_3years,  # df2
    df_price_rec_summary,  # df3

]

agent_running_stock = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0.1, model="gpt-4o-mini"),
    dataframes,
    verbose=False,
    agent_type=AgentType.OPENAI_FUNCTIONS,
    number_of_head_rows=5,
    handle_output_parsing_errors=True,
    allow_dangerous_code=True,
)

agent_visualisation = LLMChain(
    llm=ChatOpenAI(temperature=0.2, model="gpt-4o-mini"),
    prompt=prompt_template_visualisation_engineer)

agent_data_table = LLMChain(
    llm=ChatOpenAI(temperature=0.2, model="gpt-4o-mini"),
    prompt=prompt_template_final_df)
