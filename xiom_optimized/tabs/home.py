import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
from dash import State

from xiom_optimized.langchain_utils.agents import agent_running_stock
from xiom_optimized.langchain_utils.prompt_news import prompt_news
from xiom_optimized.dash_callbacks.ask_ai_callbacks import textbox
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


@app.callback(
    Output('news-content', 'children'),
    [Input('loading-news', 'children')]
)
def fetch_news(_):
    response = agent_running_stock.run(prompt_news + "share with me the latest news for the data")
    return news_box(response)
