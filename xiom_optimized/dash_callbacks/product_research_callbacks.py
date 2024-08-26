from dash import Input, Output, State
from dash.exceptions import PreventUpdate
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

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
    
    # Filter the collection based on SKU and warehouse_code
    filtered_docs = chroma_collection.get(
        where={"$and": [{"sku": {"$eq": sku}}, {"warehouse_code": {"$eq": warehouse}}]}
    )
    
    if not filtered_docs['ids']:
        return "No reviews found for the selected SKU and warehouse_code."
    
    # Create a QA chain using the existing vectorstore
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        chain_type="stuff",
        retriever=vectorstore.as_retriever(
            search_kwargs={
                "filter": {"$and": [{"sku": {"$eq": sku}}, {"warehouse_code": {"$eq": warehouse}}]}
            }
        )
    )
    
    # Run the query
    result = qa_chain.run(query)
    
    return result

# Add any other necessary callbacks for product research page