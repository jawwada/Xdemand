import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

from xiom_optimized.utils.data_fetcher import df_agg_monthly_3years
from xiom_optimized.utils.data_fetcher import df_price_rec_summary
from xiom_optimized.utils.data_fetcher import df_running_stock

from xiom_optimized.langchain_utils.prompt_news import prompt_news
from xiom_optimized.utils.cache_manager import cache_decorator


layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(
            [
                html.H2("Home Page"),
                html.Hr(),
                html.P("Welcome to your Home page!"),
                dbc.Card(
                    [
                        dbc.CardHeader("Personal Information"),
                        dbc.CardBody(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col("Name:", width=3),
                                        dbc.Col("Ahtesham Sadiq", width=9),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col("Email:", width=3),
                                        dbc.Col("Asadiq@rdxsports.com", width=9),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col("Address:", width=3),
                                        dbc.Col("UK", width=9),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col("Phone:", width=3),
                                        dbc.Col("+44 123456-7890", width=9),
                                    ],
                                    className="mb-3",
                                ),

                            ]
                        ),
                    ],
                    className="mb-4",
                ),
                html.H3("News"),
                html.Hr(),
                html.Div(
                    id='news-output', children=''
                ),
            ],
            className="content",
        ),
    ]
)

from dash import Input
from dash import Output
from dash import dcc
from dash import html
from dash.exceptions import PreventUpdate

from xiom_optimized.app_config_initial import app
from xiom_optimized.langchain_utils.agents import agent_running_stock
from xiom_optimized.langchain_utils.prompts import prompt_ds


@app.callback(
    Output('news-output', 'children'),
    [Input('url', 'pathname')]
)
def update_news_output(pathname):
    if pathname == "/":
        return html.Div([
            html.P(id="loading-news"),
            dcc.Loading(
                id="loading-news-spinner",
                children=[html.Div(id="news-content")],
                type="circle",
            )
        ])
    raise PreventUpdate

def news_box(text, name="RDX"):
    text = text.replace(f"{name}:", "")

    style = dict({ "max-width": "100%",
    "width": "max-content",
    "padding": "5px 5px",
    "border-radius": 25,
    "margin-bottom": 20
    })
    style["margin-left"] = 0
    style["margin-right"] = "auto"
    textbox = dbc.Card(dcc.Markdown(text), style=style, body=True, color="light", inverse=False)
    return html.Div([textbox])

# create agent
dataframes = [
    df_running_stock,  # df1
    df_agg_monthly_3years,  # df2
    df_price_rec_summary,  # df3
]

agent_news = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0.3, model="gpt-4o"),
    dataframes,
    verbose=False,
    agent_type=AgentType.OPENAI_FUNCTIONS,
    number_of_head_rows=5,
    allow_dangerous_code=True,
    handle_parsing_errors=True,
    max_iterations=30
)
@app.callback(
    Output('news-content', 'children'),
    [Input('loading-news', 'children')]
)
def fetch_news(_):
    response = agent_news.run(prompt_news + "share with me the latest news for the data")
    return news_box(response)
