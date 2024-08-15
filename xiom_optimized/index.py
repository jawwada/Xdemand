from dash import Input
from dash import Output

from xiom_optimized.app_config_initial import app
from xiom_optimized.app_layout import layout
from xiom_optimized.app_layout import page_layouts

# no date column
app.layout = layout


@app.callback(Output("page-content", "children"),
              [Input("tabs-navigation", "value")])
def render_content(pathname):
    if pathname in page_layouts:
        layout = page_layouts[pathname]
        return layout


server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)

# app.config['DEBUG'] = True
