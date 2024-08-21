from xiom_optimized.dash_callbacks.ask_ai_callbacks import *
from common.db_connection import engine

description = """
This is a chatbot that can answer questions about the running stock of the products in the warehouse."""

# Load images

# Define Layout
conversation = html.Div(className='col-md-12', children=[
    html.Div(id="display-conversation")],
                        style={
                            "overflow-y": "auto",
                            "display": "flex",
                            "height": "calc(90vh - 200px)",
                            "flex-direction": "column-reverse",
                            'width': '100%'
                        },
                        )

controls = dbc.InputGroup(
    children=[
        dbc.Input(id="user-input", placeholder="Write to the chatbot...", type="text"),
        dbc.Button("Submit", id="submit"),
    ]
)
# Add the clear chat button here with the id "clear-chat-button", right aligned
clear_button = dbc.Button("Clear Chat", id="clear-chat-button",
                          className="mr-2", style={"float": "right"})

layout = [
    dcc.Store(id="store-it", data=[]),
    dcc.Store(id="store-conversation", data="", storage_type="session"),
    dcc.Store(id="response-code", data="", storage_type="session"),
    dcc.Store(id="response-code-final-df", data="", storage_type="session"),

    dbc.Container(
        fluid=False,
        children=[
            Header("XD", app),
            html.Hr(),
            clear_button,  # Add the clear chat button here
            conversation,
            controls,

            dbc.Spinner(html.Div(id="loading-component")),
            html.Div(id='buttons-container', children=[
                dbc.Button("Generate Table", id="generate-table-button", className="mr-2"),
                dbc.Button("Generate Graph", id="generate-graph-button", className="mr-2")
            ]),
            html.Div(id="graph-table-container", children=''),
            html.Div(id="data-table-container", children=''),
            html.Div(id='dynamic-figure', children='')
        ],
    ),
]