from dash import Input, Output, State
from dash.exceptions import PreventUpdate
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from dash import html
from datetime import datetime

from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.data_fetcher import chroma_collection, vectorstore

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