import dash
import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

dash.register_page(__name__, path='/profile')

layout = html.Div(
    [

        html.Hr(),
        dcc.Location(id="url", refresh=False),
        html.Div(
            [
                html.H2("Profile Page"),
                html.Hr(),
                html.P("Welcome to your profile page!"),
                dbc.Card(
                    [
                        dbc.CardHeader("Personal Information"),
                        dbc.CardBody(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col("Name:", width=3),
                                        dbc.Col("Adnan Arif", width=9),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col("Email:", width=3),
                                        dbc.Col("aarif@rdxsports.com", width=9),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col("Address:", width=3),
                                        dbc.Col("123 Main St, City, Country", width=9),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col("Phone:", width=3),
                                        dbc.Col("+1 123-456-7890", width=9),
                                    ],
                                    className="mb-3",
                                ),
                            ]
                        ),
                    ],
                    className="mb-4",
                ),
                html.P("Additional profile content can be added here."),
            ],
            className="content",
        ),
    ]
)
