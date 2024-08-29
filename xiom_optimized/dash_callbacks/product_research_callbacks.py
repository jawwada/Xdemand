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
from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.data_fetcher import vectorstore
from xiom_optimized.utils.data_fetcher import df_sales, df_price_rec, df_fc_qp, df_price_rec_summary


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
    Output('merged-graph', 'children'),
    Input('sku-dropdown', 'value'),
    Input('warehouse-code-dropdown', 'value'),
    Input('filter-data', 'data')
)
def update_merged_graph(selected_sku, selected_warehouse, filter_data):
    if selected_sku is None or selected_warehouse is None:
        raise PreventUpdate
    today = pd.to_datetime("today")
    six_months_later = today + pd.DateOffset(months=6)
    year_ago = today - pd.DateOffset(months=12)

    filtered_data = pd.read_json(filter_data, orient='split')
    df_sales_filtered = df_sales.merge(filtered_data, on=['sku', 'warehouse_code'], how='inner')
    df_price_filtered = df_price_rec[
        (df_price_rec['sku'] == selected_sku) & (df_price_rec['warehouse_code'] == selected_warehouse)]
    df_fc_qp_filtered = df_fc_qp[(df_fc_qp['sku'] == selected_sku) & (df_fc_qp['warehouse_code'] == selected_warehouse)]
    df_fc_qp_filtered = df_fc_qp_filtered.groupby([pd.Grouper(key='ds', freq='W-Mon')]).sum().reset_index()
    # Filter df_price_filtered to only include data from today to the next 6 months
    df_fc_qp_filtered = df_fc_qp_filtered[ (df_fc_qp_filtered['ds'] <= six_months_later)]

    # Filter df_dsa to only include data up to today
    df_dsa = df_sales_filtered[(df_sales_filtered['date'] >= year_ago) & (df_sales_filtered['date'] <= today) & (
        df_sales_filtered['sku'].isin([selected_sku]))]
    df_dsa['date'] = pd.to_datetime(df_dsa['date'])
    df_dsa.fillna(0, inplace=True)
    df_dsa = df_dsa.groupby([pd.Grouper(key='date', freq='W-Mon')]).agg(
        {'quantity': 'sum', 'revenue': 'sum', 'price': 'mean', 'out_of_stock': 'sum'}).reset_index()
    df_dsa.set_index('date', inplace=True)

    # Filter df_price_filtered to only include data from today to the next 6 months
    df_price_filtered = df_price_filtered[
        (df_price_filtered['ds'] >= today) & (df_price_filtered['ds'] <= six_months_later)]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Weekly Sales and Price Adjustment", "Forecast, TrendY and Yearly Seasonality"),
        row_heights=[0.5,0.5],
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # Weekly Sales and Price Adjustment Graph
    fig.add_trace(go.Bar(x=df_dsa.index, y=df_dsa['quantity'], name='Quantity'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_dsa.index, y=df_dsa['quantity'].rolling(window=4).mean(), mode='lines', name='Trend'),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=df_dsa.index, y=df_dsa['price'], mode='lines', name='Price'), row=1, col=1,
                  secondary_y=True)
    fig.add_trace(
        go.Scatter(x=df_price_filtered['ds'], y=df_price_filtered['running_stock_after_forecast'], mode='lines',
                   name='Stock Non-Adjusted'), row=1, col=1,  secondary_y=True)
    fig.add_trace(
        go.Scatter(x=df_price_filtered['ds'], y=df_price_filtered['running_stock_after_forecast_adj'], mode='lines',
                   name='Stock Adjusted'), row=1, col=1, secondary_y=True)
    # Add vertical lines and annotations for Expected Arrival Dates
    for _, row in df_price_filtered[df_price_filtered['InTransit_Quantity'] != 0].iterrows():
        fig.add_vline(x=row['ds'], line=dict(color='red', dash='dash'), line_width=1, row=1, col=1)
        fig.add_annotation(x=row['ds'],  text=str(int(row['InTransit_Quantity'])),
                              showarrow=True, font=dict(color='red'), row=1, col=1)


    # Trend and Seasonality Graph
    fig.add_trace(go.Scatter(x=df_fc_qp_filtered['ds'], y=df_fc_qp_filtered['quantity'], name='Prediction'), row=2,
                  col=1)
    fig.add_trace(
        go.Scatter(x=df_fc_qp_filtered['ds'], y=df_fc_qp_filtered['q_lower'], name='Lower Bound', line=dict(width=0)),
        row=2, col=1)
    fig.add_trace(
        go.Scatter(x=df_fc_qp_filtered['ds'], y=df_fc_qp_filtered['q_upper'], name='Upper Bound', fill='tonexty'),
        row=2, col=1)
    fig.add_trace(go.Scatter(x=df_fc_qp_filtered['ds'], y=df_fc_qp_filtered['q_trend'], name='Trend'), row=2, col=1,
                  secondary_y=True)

    # Yearly Seasonality Graph
    fig.add_trace(go.Scatter(x=df_fc_qp_filtered['ds'], y=df_fc_qp_filtered['q_yearly'], name='Yearly'), row=2, col=1, secondary_y=True)

    # Update layout
    fig.update_layout(
        title_text=f'Product Graph for SKU {selected_sku}',
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.5)",
            bordercolor="Black",
            borderwidth=1
        ),
        margin=dict(l=0, r=0, t=50, b=50)  # Adjust margins to take full width
    )

    # Update y-axes titles
    fig.update_yaxes(title_text="Quantity", row=1, col=1)
    fig.update_yaxes(title_text="Price", secondary_y=True, row=1, col=1)
    fig.update_yaxes(title_text="Stock", row=1, col=1)
    fig.update_yaxes(title_text="Stock Adjusted", secondary_y=True, row=1, col=1)
    fig.update_yaxes(title_text="Forecast", row=2, col=1)
    fig.update_yaxes(title_text="Trend", secondary_y=True, row=2, col=1)
    fig.update_yaxes(title_text="Seasonality", row=3, col=1)

    # Update x-axis title
    fig.update_xaxes(title_text="Date", row=3, col=1)

    # Ensure consistent date range across all subplots
    date_range = [min(year_ago, df_price_filtered['ds'].min()), max(six_months_later, df_price_filtered['ds'].max())]
    fig.update_xaxes(range=date_range)

    return dcc.Graph(id='merged-graph-figure', figure=fig)