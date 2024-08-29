import dash_bootstrap_components as dbc
from dash import  html
from xiom_optimized.dash_callbacks.product_research_callbacks import search_reviews, update_merged_graph

layout = html.Div([
    # New section for merged graph
    html.Div(className='row', children=[
        html.Div(id='merged-graph', className='col')
    ]),
    html.Hr(),
    html.Div([
        html.H3("Review Search"),
        dbc.Input(id="search-input", type="text", placeholder="Enter your search query"),
        dbc.Button("Search", id="search-button", color="primary", className="mr-2"),
        html.Div(id="search-results", className="mt-3")
    ], className='row'),
])

