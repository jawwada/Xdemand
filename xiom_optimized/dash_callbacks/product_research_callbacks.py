from dash import Input, Output, State
from dash.exceptions import PreventUpdate
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from dash import html
from datetime import datetime
import plotly.graph_objects as go
import dash_core_components as dcc
import pandas as pd

from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.data_fetcher import vectorstore
from xiom_optimized.utils.data_fetcher import df_sales, df_price_rec

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
    Input('warehouse-code-dropdown', 'value'),
    prevent_initial_call=True
)
def update_weekly_sales_graph(selected_sku, selected_warehouse):
    if selected_sku is None or selected_warehouse is None:
        raise PreventUpdate
    # Fetch weekly sales data for the past year
    weekly_sales_data = df_sales[(df_sales['sku'] == selected_sku) &
                                           (df_sales['warehouse_code'] == selected_warehouse)]
    
    # Ensure data is not older than 365 days from the max date
    max_date = weekly_sales_data['date'].max()
    cutoff_date = max_date - pd.DateOffset(days=365)
    weekly_sales_data = weekly_sales_data[weekly_sales_data['date'] >= cutoff_date]

    # Group by week
    weekly_sales_data = weekly_sales_data.groupby(pd.Grouper(key='date', freq='W-Mon')).agg({
        'quantity': 'sum',
        'price': 'mean',
        'out_of_stock': 'sum'
    }).reset_index()

    # Create the weekly sales graph
    sales_fig = go.Figure()
    sales_fig.add_trace(go.Scatter(x=weekly_sales_data['date'], y=weekly_sales_data['quantity'], mode='lines', name='Weekly Sales'))
    
    # Create the promotional rebates graph
    rebates_fig = go.Figure()
    rebates_fig.add_trace(go.Bar(x=weekly_sales_data['date'], y=weekly_sales_data['price'], name='Price'))

    # Create the OOS days graph
    oos_days_fig = go.Figure()
    oos_days_fig.add_trace(go.Bar(x=weekly_sales_data['date'], y=weekly_sales_data['out_of_stock'], name='Out of Stock Days'))

    return [
        dcc.Graph(figure=sales_fig),  # Weekly Sales Graph
        dcc.Graph(figure=rebates_fig),  # Promotional Rebates Graph
        dcc.Graph(figure=oos_days_fig)  # OOS Days Graph
    ]
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
    Input('sku-dropdown', 'value'),
    Input('warehouse-code-dropdown', 'value'),
)
def update_trend_seasonality_graph(selected_sku, selected_warehouse):
    if selected_sku is None or selected_warehouse is None:
        raise PreventUpdate
    # Fetch data for running stock after forecast and adjusted forecast
    running_stock_data = df_price_rec[(df_price_rec['sku'] == selected_sku) & 
                                       (df_price_rec['warehouse_code'] == selected_warehouse)]
    
    # Create the trend and seasonality graph
    trend_seasonality_fig = go.Figure()
    
    # Add trend and seasonality data
    trend_seasonality_fig.add_trace(go.Scatter(
        x=running_stock_data['ds'], 
        y=running_stock_data['trend'], 
        mode='lines', 
        name='Trend',
        line=dict(color='orange')
    ))
    
    trend_seasonality_fig.add_trace(go.Scatter(
        x=running_stock_data['ds'], 
        y=running_stock_data['yearly_seasonality'],
        mode='lines', 
        name='Seasonality',
        line=dict(color='red')
    ))
    
    trend_seasonality_fig.update_layout(title='Trend and Seasonality',
                                        xaxis_title='Date',
                                        yaxis_title='Value')
    
    return trend_seasonality_fig