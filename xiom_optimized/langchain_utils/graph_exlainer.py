import base64
import io
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.io as pio
from PIL import Image
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class GraphExplainer:
    def __init__(self, app, model="gpt-4-1106-preview"):
        self.app = app
        self.model = ChatOpenAI(temperature=0.1, model=model)
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a data visualization expert. Provide a detailed explanation of the graph."),
            ("user", "{graph_description}")
        ])

    def register_callbacks(self):
        @self.app.callback(
            Output('graph-description', 'children'),
            Input('explain-button', 'n_clicks'),
            State('graph-id', 'figure')
        )
        def explain_graph(n_clicks, figure):
            if n_clicks is None:
                return ""
            img_bytes = pio.to_image(figure, format='png')
            img = Image.open(io.BytesIO(img_bytes))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            graph_description = f"![Graph](data:image/png;base64,{img_str})"
            response = self.model.invoke({"graph_description": graph_description})
            return response.content

    def get_explain_button(self, graph_id):
        return html.Div([
            dcc.Graph(id=graph_id),
            html.Button('AI Explain', id='explain-button'),
            html.Div(id='graph-description')
        ])
