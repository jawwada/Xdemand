from dash import Input, Output, State
from dash.exceptions import PreventUpdate
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from dash import html
from datetime import datetime
import plotly.graph_objects as go
import dash_core_components as dcc
import pandas as pd
from plotly.subplots import make_subplots
from xiom_optimized.utils.config_constants import sample_rate_dict
from prophet import Prophet

from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.data_fetcher import vectorstore
from xiom_optimized.utils.data_fetcher import df_sales, df_price_rec, df_fc_qp


@app.callback(
    Output("search-results", "children"),
    Input("search-button", "n_clicks"),
    State("sku-dropdown", "value"),
    State("warehouse-code-dropdown", "value"),
    State("search-input", "value"),
    prevent_initial_call=True
)
def search_reviews(n_clicks, sku, warehouse, query):
    if query is None:
        raise PreventUpdate

    if sku is None:
        sku = "WAN-W5B+"
    if warehouse is None:
        warehouse = "UK"
    
    # Create a retriever from the vectorstore
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "filter": {"$and": [{"sku": {"$eq": sku}}, {"warehouse_code": {"$eq": warehouse}}]},
            "k": 10  # Retrieve top 50 most relevant reviews
        }
    )
    
    # Retrieve relevant documents
    relevant_docs = retriever.get_relevant_documents(query)
    
    if not relevant_docs:
        return "No relevant reviews found for the given query, SKU, and warehouse_code."
    
    # Sort relevant_docs by date in descending order
    sorted_docs = sorted(relevant_docs, key=lambda x: datetime.strptime(x.metadata['date'], '%Y-%m-%d'), reverse=True)
    
    # Take only the top 10 reviews
    top_10_docs = sorted_docs[:10]
    
    # Create a QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        chain_type="stuff",
        retriever=retriever
    )
    
    # Run the query
    result = qa_chain.run(query)
    
    # Create table header
    table_header = [
        html.Tr([
            html.Th("Date"),
            html.Th("Rating"),
            html.Th("SKU"),
            html.Th("Warehouse"),
            html.Th("Title"),
            html.Th("Review"),
        ])
    ]
    
    # Create table rows
    table_rows = []
    for doc in top_10_docs:
        metadata = doc.metadata
        table_rows.append(html.Tr([
            html.Td(metadata['date']),
            html.Td(metadata['rating']),
            html.Td(metadata['sku']),
            html.Td(metadata['warehouse_code']),
            html.Td(metadata['title']),
            html.Td(doc.page_content),
        ]))
    
    # Create the table
    review_table = html.Table(table_header + table_rows)
    
    # Combine AI answer and review table
    final_output = html.Div([
        html.H3("AI Answer:"),
        html.P(result),
        html.H3("Top 10 Most Recent Relevant Reviews:"),
        review_table
    ])
    
    return final_output

# Add any other necessary callbacks for product research page

@app.callback(
    Output('weekly-sales-graph', 'children'),
   Input('sku-dropdown', 'value'),
    Input('filter-data', 'data')
)
def update_sku_price_relationship_graph(selected_sku=None, filter_data=None):
    filtered_data = pd.read_json(filter_data, orient='split')
    if selected_sku is None:
        selected_sku = []
    elif isinstance(selected_sku, str):
        selected_sku = [selected_sku]
    else:
        selected_sku = filtered_data['sku'].unique()

    df_sales_filtered = df_sales.merge(filtered_data, on=['sku', 'warehouse_code'], how='inner')
    today = pd.to_datetime("today")

    year_ago = today - pd.DateOffset(months=14)
    df_dsa = df_sales_filtered[(df_sales_filtered['date'] >= year_ago) & (df_sales_filtered['sku'].isin(selected_sku))]

    df_dsa['date'] = pd.to_datetime(df_dsa['date'])
    df_dsa.fillna(0, inplace=True)
    df_dsa = df_dsa.groupby([pd.Grouper(key='date', freq='W-Mon')]). \
        agg({'quantity': 'sum', 'revenue': 'sum', 'price': 'mean', 'out_of_stock': 'sum'}).reset_index()
    df_dsa.set_index('date', inplace=True)
    sku = selected_sku
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        subplot_titles=("Main Plot", "Stockouts"), row_heights=[0.7, 0.3],
                        specs=[[{"secondary_y": True}], [{}]])

    fig.add_trace(go.Bar(x=df_dsa.index, y=df_dsa['quantity'], name='Quantity'), row=1, col=1, secondary_y=False)
    fig.add_trace(
        go.Scatter(x=df_dsa.index, y=df_dsa['quantity'].rolling(window=4).mean(), mode='lines', name='Trend'), row=1,
        col=1, secondary_y=False)

    fig.add_trace(go.Scatter(x=df_dsa.index, y=df_dsa['price'], mode='lines', name='Price'), row=1, col=1,
                  secondary_y=True)

    fig.add_trace(go.Bar(x=df_dsa.index, y=df_dsa['out_of_stock'], name='Out of Stock Days'), row=2, col=1)

    fig.update_layout(
        title_text=f'Selling Price and Volume Timeline SKU {sku}',
        legend=dict(
            x=-0.1,  # Position the legend to the left
            y=1,
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
                color='black'
            ),
            bgcolor='LightSteelBlue',
            bordercolor='Black',
            borderwidth=2
        )
    )
    fig.update_yaxes(title_text="Price", secondary_y=True)

    return dcc.Graph(id='sku-sales-oos-graph', figure=fig)

@app.callback(
    Output('price-adjustment-graph', 'children'),
    Input('sku-dropdown', 'value'),
    Input('warehouse-code-dropdown', 'value'),
)
def update_price_adjustment_graph(selected_sku, selected_warehouse):
    if selected_sku is None or selected_warehouse is None:
        raise PreventUpdate
    # Fetch price adjustment data
    price_data = df_price_rec[(df_price_rec['sku'] == selected_sku) & (df_price_rec['warehouse_code'] == selected_warehouse)]
    
    # Create the price adjustment graph
    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(x=price_data['ds'], y=price_data['running_stock_after_forecast'], mode='lines', name='Price Non-Adjusted'))
    price_fig.add_trace(go.Scatter(x=price_data['ds'], y=price_data['running_stock_after_forecast_adj'], mode='lines', name='Price Adjusted'))
    
    return dcc.Graph(figure=price_fig)

@app.callback(
    Output('trend-seasonality-graph', 'figure'),
    [Input('sample-rate-slider', 'value'),
    Input('sku-dropdown', 'value'),
    Input('warehouse-code-dropdown', 'value')],
    prevent_initial_call = True
)
def update_trend_seasonality_graph(time_window,
                                 selected_sku,selected_warehouse):
    if isinstance(selected_sku, str) and isinstance(selected_warehouse, str):
        today = pd.to_datetime("today")

        # Calculate the date range (today ± 6 months)
        six_months_later = today + pd.DateOffset(months=6)
        df_fc_qp_filtered = df_fc_qp[(df_fc_qp['ds'] <= six_months_later)]

        # 1 year ago
        one_year_ago = today - pd.DateOffset(months=12)
        df_fc_qp_filtered = df_fc_qp_filtered[(df_fc_qp_filtered['ds'] >= one_year_ago)]

        df_ds = df_fc_qp_filtered[df_fc_qp_filtered['sku'] == selected_sku]
        df_ds = df_ds[df_ds['warehouse_code'] == selected_warehouse]

        # Create subplots: use 'domain' type for Pie subplot
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.01,
                            subplot_titles=("Forecast", "Trend", "Seasonality"))

        forecast = df_ds
        # Add forecast data
        fig.add_trace(go.Scatter(x=df_ds['ds'], y=df_ds['quantity'], name='prediction'), row=1, col=1)

        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['q_lower'], name='Lower Bound of Forecast',
                                 line=dict(width=0)), row=1, col=1)
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['q_upper'], name='Upper Bound of Forecast',
                                 fill='tonexty'), row=1, col=1)

        # Add trend data
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['q_trend'], name='Trend'), row=2, col=1)
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['q_yearly'], name='Yearly'), row=3, col=1)

        # Update layout
        fig.update_layout(title=f'RDX Demand Forecast: sku = {selected_sku}', height=400)
        fig.update_yaxes(title_text="Value", row=1, col=1)
        fig.update_yaxes(title_text="Trend Value", row=2, col=1)
        fig.update_yaxes(title_text="Seasonality Value", row=3, col=1)
        fig.update_xaxes(title_text="Date", row=3, col=1)

        return html.Div([
            dcc.Graph(id='trend-seasonality-graph', figure=fig)
        ])
