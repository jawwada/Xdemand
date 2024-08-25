import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

from xiom_optimized.langchain_utils.agents import agent_running_stock
from xiom_optimized.langchain_utils.prompts import prompt_ds

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
                dcc.Textarea(
                    id='news-text',
                    placeholder='Enter your question here...',
                    style={'width': '100%', 'height': 100},
                ),
                html.Div(id='news-output'),
            ],
            className="content",
        ),
    ]
)

from dash import Input
from dash import Output
from dash import dcc
from dash import html

from xiom_optimized.app_config_initial import app
from xiom_optimized.langchain_utils.agents import agent_running_stock
from xiom_optimized.langchain_utils.prompts import prompt_ds

@app.callback(
    Output('news-output', 'children'),
    Input('news-text', 'value')
)
def update_news_output(question):
    if question is None:
        question = "What is the latest news on data?"
        return ""
    response = agent_running_stock.run(prompt_ds + question)
    return html.Div(response)
