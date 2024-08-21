import logging

import dash_core_components as dcc
import dash_html_components as html
import dash_table

from xiom_optimized.langchain_utils.agents import agent_visualisation
from xiom_optimized.utils.data_fetcher import df_agg_monthly_3years as df2
from xiom_optimized.utils.data_fetcher import df_price_rec_summary as df3
from xiom_optimized.utils.data_fetcher import df_running_stock as df1

logger = logging.getLogger(__name__)


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
        logger.info(f"Plotly agent response: {plotly_agent_response}")
        fig = get_fig_from_code(plotly_agent_response["text"])
        return dcc.Graph(figure=fig)
    except Exception as e:
        print(e)
        return html.Div("Error generating graph")
