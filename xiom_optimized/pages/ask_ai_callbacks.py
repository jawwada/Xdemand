from dash.dependencies import Input, Output, State
from xiom_optimized.chat_agent import agent_running_stock, prompt
from xiom_optimized.app_config_initial import app
import dash_bootstrap_components as dbc
from dash import html, dcc

IMAGES = {"XD": app.get_asset_url("home_img.png")}


def Header(name, app):
    title = html.H4(name, style={"margin-top": 5})
    logo = html.Img(
        src=app.get_asset_url("home_img.png"), style={"float": "right", "height": 40}
    )
    return dbc.Row([dbc.Col(title, md=10), dbc.Col(logo, md=2)])


def textbox(text, box="AI", name="RDX"):
    text = text.replace(f"{name}:", "").replace("You:", "")
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
    if chat_history!="":
        return [
            textbox(x, box="user") if i % 2 == 0 else textbox(x, box="AI")
            for i, x in enumerate(chat_history.split("<split>")[:-1])
        ]
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
     Output("loading-component", "children")],
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
    chat_history += f"You {user_input}<split>"
    model_input = f"{prompt}\n  chat_history:\n {chat_history} \n User Input: {user_input}\n"
    response = agent_running_stock.run(model_input)
    chat_history += f"{response}<split>"
    return chat_history, None
