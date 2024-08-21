import base64
import io
import logging
import traceback

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc
from dash import html
from dash.dependencies import Input
from dash.dependencies import Output
from dash.dependencies import State
from sqlalchemy import text

from xiom_optimized.app_config_initial import app
from xiom_optimized.langchain_utils.agent_executor_custom_call_backs import CustomHandler
from xiom_optimized.langchain_utils.agents import agent_data_table
from xiom_optimized.langchain_utils.agents import agent_running_stock
from xiom_optimized.langchain_utils.dangerous_code import generate_graph
from xiom_optimized.langchain_utils.dangerous_code import generate_table
from xiom_optimized.langchain_utils.dangerous_code import get_final_df_from_code
from xiom_optimized.langchain_utils.prompts import prompt_ds
from common.db_connection import engine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

IMAGES = {"XD": app.get_asset_url("img.png")}
custom_callback = CustomHandler(app)


def Header(name, app):
    title = html.H4(name, style={"margin-top": 5})
    logo = html.Img(
        src=app.get_asset_url("img.png"), style={"float": "right", "height": 40}
    )
    return dbc.Row([dbc.Col(title, md=10), dbc.Col(logo, md=2)])


def textbox(text, box="AI", name="RDX"):
    text = text.replace(f"{name}:", "")
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
            src=app.get_asset_url("img.png"),
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
    [Output("display-conversation", "children"),
     Output("response-code", "data"),
     Output("store-conversation", "data"),
     Output("user-input", "value")],
    [Input("submit", "n_clicks"),
     Input("user-input", "n_submit"),
     Input("clear-chat-button", "n_clicks"),
     Input("warehouse-code-dropdown", "value"),
     Input("category-dropdown", "value"),
     Input("sku-dropdown", "value")],
    [State("store-conversation", "data"),
     State("user-input", "value")],
)
def run_chatbot(n_clicks, n_submit, clear_clicks, warehouse_code, category, sku, chat_history, user_input):
    ctx = dash.callback_context
    # check if the callback was triggered by the clear chat button
    if ctx.triggered[0]["prop_id"] == "clear-chat-button.n_clicks":
        return "", "", "", None  # Reset user input to None

    if ctx.triggered[0]["prop_id"] != "submit.n_clicks":
        return "", "", chat_history, None  # Reset user input to None

    focus_area = []
    if warehouse_code is not None:
        focus_area.append(f"Warehouse: {warehouse_code}")
    if category is not None:
        focus_area.append(f"Category: {category}")
    if sku is not None:
        focus_area.append(f"SKU: {sku}")

    if focus_area:
        user_input = user_input.strip() + ". Focus Area: " + "\n ".join(focus_area) + "\n"
    # Use warehouse_code, category, and sku as needed in your logic
    name = "Xd"
    chat_history += f"You : {user_input} <split>"
    model_input = (f"{prompt_ds}\n  chat_history:\n {chat_history} \n User Input: {user_input}")
    chat_response = agent_running_stock.run(model_input, callbacks=[custom_callback])
    response_code = custom_callback.response_code

    if chat_response:
        # Assuming `engine` is already defined and connected
        data = {
            "UserName": ["User"],
            "Question": [user_input],
            "response_code": [response_code],
            "Answer": [chat_response],
            "Thumbs": [None],  # Replace None with an actual value for thumbs if needed
            "CreatedAt": [pd.Timestamp.now()]
        }
        # Insert the DataFrame into the database
        pd.DataFrame(data).to_sql('stg_tr_chat_history',
                                  con=engine, if_exists='append', index=False)

    chat_history += f"{chat_response}<split>"
    return [textbox(x, box="user") if i % 2 == 0 else textbox(x, box="AI")
                 for i, x in enumerate(chat_history.split("<split>")[:-1])
        ], response_code, chat_history, None  # Reset user input to None


@app.callback(Output("response-code-final-df", "data"),
              Input("response-code", "data")
              )
def update_final_df(response_code):
    if response_code == None or response_code == "":
        return ""
    try:
        response_code_final_df = agent_data_table.invoke(response_code)
        print(response_code_final_df)
    except Exception as e:
        print(f"Error in update_final_df: {str(e)}")
        response_code_final_df = ""
    return response_code_final_df["text"]


@app.callback(
    Output("graph-table-container", "children"),
    [Input("generate-table-button", "n_clicks"),
     Input("generate-graph-button", "n_clicks")],
    State("response-code-final-df", "data")
)
def update_graph_table_container(table_clicks, graph_clicks, response_code_final_df):
    if response_code_final_df == "":
        return None
    final_df_code = response_code_final_df
    ctx = dash.callback_context
    if not ctx.triggered:
        return None
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "generate-table-button":
        return generate_table(final_df_code)
    elif button_id == "generate-graph-button":
        return generate_graph(final_df_code)


@app.callback(
    Output('download-button-final-df', 'href'),
    Input('response-code-final-df', 'data')
)
def update_download_link(response_code_final_df):
    if response_code_final_df == "":
        return ""
    try:
        final_df = get_final_df_from_code(response_code_final_df)
        # Create an in-memory Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='Sheet1', index=False)

        # Encode the Excel file to base64
        excel_bytes = output.getvalue()
        b64 = base64.b64encode(excel_bytes).decode()

        return f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"
    except Exception as e:
        print(f"Error in update_download_link: {str(e)}")
        print(traceback.format_exc())
        return ""


@app.callback(
    Output("download-dataframe-xlsx", "data"),
    Input("download-button-final-df", "n_clicks"),
    State("response-code-final-df", "data"),
    prevent_initial_call=True,
)
def download_xlsx(n_clicks, response_code_final_df):
    try:
        final_df = get_final_df_from_code(response_code_final_df)
        return dcc.send_data_frame(final_df.to_excel, "final_dataframe.xlsx", sheet_name="Sheet1")
    except Exception as e:
        print(f"Error in download_xlsx: {str(e)}")
        return None