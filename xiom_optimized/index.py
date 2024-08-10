from xiom_optimized.app_layout import layout, page_layouts
from xiom_optimized.caching import *
from dash import Input, Output

# no date column
app.layout=layout

@app.callback(Output("page-content", "children"),
              [Input("tabs-navigation", "value")])
def render_content(pathname):
    if pathname in page_layouts:
        layout = page_layouts[pathname]
        return layout



server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)

#app.config['DEBUG'] = True