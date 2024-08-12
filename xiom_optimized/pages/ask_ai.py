from xiom_optimized.pages.ask_ai_callbacks import *
import pandas as pd
from dash import html
from dash import dcc
import dash_bootstrap_components as dbc
import dash_table

description = """
This is a chatbot that can answer questions about the running stock of the products in the warehouse."""

# Load images

# Define Layout
conversation = html.Div(className='col-md-12',  children=[
    html.Div(id="display-conversation")],
    style={
        "overflow-y": "auto",
        "display": "flex",
        "height": "calc(90vh - 200px)",
        "flex-direction": "column-reverse",
        'width':'100%'
    },
)

controls = dbc.InputGroup(
    children=[
        dbc.Input(id="user-input", placeholder="Write to the chatbot...", type="text"),
        dbc.Button("Submit", id="submit"),
    ]
)


layout = [
    dcc.Store(id="store-it", data=[]),
    dcc.Store(id="store-conversation", data="", storage_type="session"),
    dbc.Container(
        fluid=False,
        children=[
            Header("Inventory Assistant", app),
            html.Hr(),
            conversation,
            controls,
            dbc.Spinner(html.Div(id="loading-component")),
            html.Div(id="data-table-container") ,
            html.Div(id='dynamic-figure', children='')# Container for the DataTable
        ],
    ),
]

