import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

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
            ],
            className="content",
        ),
    ]
)
