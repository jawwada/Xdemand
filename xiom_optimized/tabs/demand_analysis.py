from xiom_optimized.dash_callbacks.demand_analysis_callbacks import *
content = html.Div([
    # Forecasting Graphs
    html.Div([
        dcc.Tabs(id="analysis-tabs", value='da-tab-1', children=[
            dcc.Tab(label='Graph', value='da-tab-1'),
            dcc.Tab(label='Data', value='da-tab-2'),
        ]),
        html.Div(id='da-tabs-content-analysis'),
        html.Hr(),
    ], className="col")
])

layout = html.Div([
    html.Div([
        html.Div([content], style={'margin-left': '0px'})
    ], className="row")
], className="col-md-12")
