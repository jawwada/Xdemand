from xiom_optimized.dash_callbacks.demand_analysis_callbacks import *

content = html.Div([
    # Forecasting Graphs
    dcc.Store(id='fig-store'),
    html.Div([
        html.Div([
            html.Button("Explain AI", id="explain-ai-analysis", className="mr-2", style={"float": "right"}),
            dcc.Tabs(id="analysis-tabs", value='da-tab-1', children=[
                dcc.Tab(label='Graph', value='da-tab-1'),
                dcc.Tab(label='Data', value='da-tab-2'),
            ]),
            html.Div(id='da-tabs-content-analysis'),
            html.Hr(),
        ], className="col"),
    ]),
])

layout = html.Div([
    html.Div([
        html.Div([content], style={'margin-left': '0px'})
    ], className="row")
], className="col-md-12")