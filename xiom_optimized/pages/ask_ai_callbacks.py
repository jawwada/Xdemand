from dash.dependencies import Input, Output, State
from xiom_optimized.chat_agent import (agent_running_stock,
                                       agent_remove_code_block,
                                        agent_extract_code_block,
                                        agent_visualisation,
                                       prompt_ds)
from xiom_optimized.app_config_initial import app
import dash_bootstrap_components as dbc
from dash import html, dcc
import re
import base64
import io
from xiom_optimized.caching import df_running_stock as df1, \
    df_price_rec_summary as df3, \
    df_agg_monthly_3years as df2

IMAGES = {"XD": app.get_asset_url("home_img.png")}

def get_fig_from_code(code):
    local_variables = {}
    global_variables = {'df1': df1, 'df2': df2, 'df3': df3}
    exec(code, global_variables, local_variables)
    return local_variables['fig']

def remove_code_blocks(text):
    response = agent_remove_code_block.run(text)
    return response

def Header(name, app):
    title = html.H4(name, style={"margin-top": 5})
    logo = html.Img(
        src=app.get_asset_url("home_img.png"), style={"float": "right", "height": 40}
    )
    return dbc.Row([dbc.Col(title, md=10), dbc.Col(logo, md=2)])

def textbox(text, box="AI", name="RDX"):
    text = text.replace(f"{name}", "").replace(":", "")
    style = {
        "max-width": "100%",
        "width": "max-content",
        "padding": "5px 5px",
        "border-radius": 25,
        "margin-bottom": 20,
    }

    if box == "user":
        style["margin-left"] = "auto"
        style["margin-right"] = 0
        return dbc.Card(text, style=style, body=True, color="primary", inverse=True)

    elif box == "AI":
        style["margin-left"] = 0
        style["margin-right"] = "auto"

        thumbnail = html.Img(
            src=app.get_asset_url("home_img.png"),
            style={
                "height": 40,
                "float": "left",
            },
        )
        textbox = dbc.Card(dcc.Markdown(text), style=style, body=True, color="light", inverse=False)

        return html.Div([thumbnail, textbox])

    else:
        raise ValueError("Incorrect option for `box`.")

@app.callback(
    Output("display-conversation", "children"),
    [Input("store-conversation", "data")]
)
def update_display(chat_history):
    if chat_history != "":
        response = [
            textbox(x, box="user") if i % 2 == 0 else textbox(x, box="AI")
            for i, x in enumerate(chat_history.split("<split>")[:-1])
        ]
        return response
    else:
        return None

@app.callback(
    Output("user-input", "value"),
    [Input("submit", "n_clicks"),
     Input("user-input", "n_submit")],
)
def clear_input(n_clicks, n_submit):
    return ""

@app.callback(
    [Output("store-conversation", "data"),
     Output("loading-component", "children"),
     Output("dynamic-figure", "children")],
    [Input("submit", "n_clicks"),
     Input("user-input", "n_submit")],
    [State("user-input", "value"),
     State("store-conversation", "data")],
)
def run_chatbot(n_clicks, n_submit, user_input, chat_history):
    if n_clicks == 0 and n_submit is None:
        return "", None

    if user_input is None or user_input == "":
        return chat_history, None

    name = "Xd"
    # First add the user input to the chat history
    chat_history += f"You: {user_input}<split>:"
    model_input = f"{prompt_ds}\n  chat_history:\n {chat_history}\n User Input:{user_input}\n"
    response = agent_running_stock.run(model_input)
    response_text = remove_code_blocks(response)
    response_code = agent_extract_code_block.invoke(response)
    plotly_agent_response = agent_visualisation.invoke(response_code)
    print(plotly_agent_response["text"])
    chat_history += f"{response_text}<split>"
    try:
        fig = get_fig_from_code(plotly_agent_response["text"])
        fig=dcc.Graph(figure=fig)
        return chat_history, None, fig
    except(Exception) as e:
        print(e)
        return chat_history, None, None
