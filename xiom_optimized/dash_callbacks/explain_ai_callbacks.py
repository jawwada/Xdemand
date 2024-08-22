import base64
import io
from dash import callback_context
from dash.dependencies import Input, Output, State
from xiom_optimized.langchain_utils.agents import agent_explain_page
from PIL import Image

def register_explain_ai_callback(app):
    @app.callback(
        Output("explain-ai-store", "data"),  # Store the explanation here
        Output("explanation-output", "value"),  # Update the text area with the explanation
        Input("explain-ai-button", "n_clicks"),
        State("explain-ai-button", "data-screenshot"),
        State("current-page-content", "data"),  # Assuming you have a way to get the current page content
        prevent_initial_call=True,
    )
    def explain_ai(n_clicks, screenshot, page_content):
        if screenshot:
            # Decode the base64 image
            header, encoded = screenshot.split(',', 1)
            image_data = base64.b64decode(encoded)
            image = Image.open(io.BytesIO(image_data))

            # Process the image with the existing agent
            response = agent_visualisation.invoke({"image": image})

            # Use the new agent to explain the current page
            explanation_response = agent_explain_page.invoke({"page_content": page_content})

            # Return the explanation to the store and the text area
            return explanation_response, explanation_response

        return "", ""