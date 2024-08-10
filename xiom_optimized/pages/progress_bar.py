from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from xiom_optimized.app_config_initial import app

progress_bar_layout = html.Div([
dbc.Progress(id="progress_bar", value=0, striped=True, animated=True, style={'width': '100%', 'color': '#0000FF'}),
dcc.Interval(id="progress_interval", interval=100, n_intervals=0),  # Timer for updating progress bar
 ])

@app.callback(
    Output('progress_bar', 'value'),
    Output('progress_bar', 'style'),
    Output('progress_interval', 'interval'),
    Input('progress_interval', 'n_intervals')
)
def update_progress_bar(n):
    # Logic to update progress bar value
    progress = calculate_progress(n)  # Replace with your logic
    if progress >= 100:
        return 0, {'display': 'none'}, 100000000000000
    return progress, {'width': '{}%'.format(progress)}, 100

# Function to calculate progress (example)
def calculate_progress(n):
    # Replace with your logic to calculate progress
    return min(n * 5, 100)