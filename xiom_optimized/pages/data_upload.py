import dash_table
from dash import dcc, html
from xiom_optimized.utils.data_fetcher import df_sku_sum

def generate_table(max_rows=10):

    dataframe=df_sku_sum.copy(deep=True)
    sales_table = dash_table.DataTable(
        id='sales-data-table',
        columns=[{"name": i, "id": i} for i in dataframe.columns],
        data=dataframe.to_dict('records'),
        page_size=12,
        style_table={'overflow': 'hidden','textOverflow': 'ellipsis'},
        sort_action="native",
        sort_mode="multi",
        style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal', 'height': 'fixed', },
        style_header={'fontWeight': 'bold'},
        style_data_conditional=[{'if': {'row_index': 'odd'}}, {'if': {'row_index': 'even'}}]
    )
    return sales_table


layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(
            [
                html.H2("Data Page"),
                html.Hr(),
                html.P("Welcome to your Data Upload page!"),
                generate_table(100),

                html.P("Additional Data content can be added here."),
            ],
            className="content",
        ),
    ]
)

