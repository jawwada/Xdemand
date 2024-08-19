from xiom_optimized.dash_callbacks.demand_forecasting_callbacks import *
content = html.Div([
    # Forecasting Graphs
    dcc.RadioItems(
        id='seasonality-mode-radio',
        options=[
            {'label': 'Multiplicative', 'value': 'multiplicative'},
            {'label': 'Additive', 'value': 'additive'}
        ],
        value='additive',  # Default value set to 'multiplicative'
        labelStyle={'display': 'inline-block'}
    ),
    dcc.Tabs(id="demand-tabs", value='tab-1', children=[
        dcc.Tab(label='Graph', value='tab-1'),
        dcc.Tab(label='Data', value='tab-2'),
    ]),
    html.Div([
        html.Div(id='tabs-content')
    ], className="row"),
    html.Hr(),
], className="col-md-12")

layout = content
