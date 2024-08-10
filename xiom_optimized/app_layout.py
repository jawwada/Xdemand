import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State

from xiom_optimized.app_config_initial import app
from xiom_optimized.pages.data_chooser import data_chooser
from xiom_optimized.pages.data_upload import layout as data_upload_layout
from xiom_optimized.pages.demand_analysis import layout as demand_analysis_layout
# Import your individual layout functions from the respective modules
from xiom_optimized.pages.demand_forecasting import layout as demand_forecasting_layout
from xiom_optimized.pages.home import layout as home_layout
from xiom_optimized.pages.ask_ai import layout as inventory_planning_layout
from xiom_optimized.pages.price_sensing import layout as price_sensing_layout
from xiom_optimized.pages.profile import layout as profile_layout
from xiom_optimized.pages.stock_sensing import layout as stockout_prediction_layout
from xiom_optimized.pages.progress_bar import progress_bar_layout

# Define a dictionary for mapping the pathname to the layout of the corresponding page
page_layouts = {
    "/demand-forecasting": demand_forecasting_layout,
    "/demand-analysis": demand_analysis_layout,
    "/price-sensing": price_sensing_layout,
    "/stockout-prediction": stockout_prediction_layout,
    "/inventory-planning": inventory_planning_layout,
    "/profile": profile_layout,
    "/data-upload": data_upload_layout,
     "/":  home_layout,
}

# Callback to update progress bar



layout = html.Div(id='page_container',
        children=[
        progress_bar_layout,
        dcc.Location(id='url', refresh=False),
            dbc.Row(
            [
                dbc.Col(
                    dbc.NavLink(
                        html.Img(src=app.get_asset_url('home_img.png'),
                                 style={'height': '80px', 'width': '80px', 'float': 'left'}),
                        href="/", active="exact"),
                    width="auto"
                ),
                dbc.Col(
                    html.H4("XDemand.AI Transform Your Online Business with AI-Driven Planning",
                            className="text-center mb-6"),
                    width=True
                ),
                dbc.Col(
                    dbc.Nav(
                        [
                            dbc.NavLink("Data Upload", href="/data-upload", active="exact"),
                            dbc.NavLink("Profile", href="/profile", active="exact"),
                        ],
                        className="nav",
                        pills=True,
                    ),
                    width="auto"
                ),
            ],
            align="center",
            justify="between",
            className="header",
        ),
        html.Hr(),
        dbc.Row(
            [
                html.Div([
                    dbc.Col([
                        html.Div([
                        dcc.Tabs(
                            id="tabs-navigation",
                            vertical=True,
                            value="/",
                            className="nav nav-pills",
                            style={'float': 'left',  'width': '100%'},
                            # Set "Demand Forecasting" as the default tab
                            children=[
                                dcc.Tab(label=" Demand Analysis ", value="/demand-analysis"),
                                dcc.Tab(label=" Demand Forecasting ", value="/demand-forecasting"),
                                dcc.Tab(label=" Price Sensing ", value="/price-sensing"),
                                dcc.Tab(label=" Stock Sensing ", value="/stockout-prediction"),
                                dcc.Tab(label=" Ask AI ", value="/inventory-planning")
                            ]),
                        ], className="row", style={'width': 'auto'}),
                    html.Hr(),
                    html.Div([data_chooser])
                ]),
                ], className="col-md-2", style={'float': 'left','border-right': '5px solid #ddd'}),

                dbc.Col([
                    dbc.Spinner(
                        html.Div(id="page-content", className="col-md-12"),
                        color="primary",  # You can choose the color of the spinner
                        type="border",  # Spinner type
                        fullscreen=False,  # This can be set to True if you want the spinner to cover the entire view
                        # Spinner will be displayed when the "page-content" Div is being updated
                    ),
                ], width=10),
            ]
        )
    ]
)
from dash import callback_context

@app.callback(
    [Output('sku-dropdown', 'style'),
     Output('warehouse-code-dropdown', 'style'),
     Output('region-dropdown', 'style'),
     Output('channel-dropdown', 'style'),
     Output('dim-selector', 'style'),
     Output('time-selector', 'style'),
     Output('data-chooser', 'style')],
    [Input('tabs-navigation', 'value')],
)
def toggle_dropdown_visibility(selected_tab):
    # Default style for all dropdowns
    default_style = {}
    hidden_style = {'display': 'none'}

    # Initialize all dropdowns to be visible
    sku_style = warehouse_style = region_style = channel_style = \
    dim_style = time_style = data_chooser_style = default_style

    # Hide specific dropdowns based on the selected tab
    if selected_tab == '/demand-forecasting':
        data_chooser_style= default_style
    elif selected_tab == '/':
        data_chooser_style = hidden_style
    elif selected_tab == '/demand-analysis':
        sku_style = hidden_style
    elif selected_tab == '/price-sensing':
        channel_style = region_style = dim_style = time_style = hidden_style
    elif selected_tab == '/stockout-prediction':
        channel_style = region_style = dim_style = time_style = hidden_style
    elif selected_tab == '/inventory-planning':
        data_chooser_style = hidden_style
    return sku_style, warehouse_style, region_style, channel_style, dim_style, time_style, data_chooser_style
