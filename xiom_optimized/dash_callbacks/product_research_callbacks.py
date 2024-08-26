from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from xiom_optimized.app_config_initial import app
from xiom_optimized.utils.data_fetcher import chroma_client
from xiom_optimized.utils.data_fetcher import chroma_collection
from xiom_optimized.utils.data_fetcher import embeddings


@app.callback(
    Output("search-results", "children"),
    Input("search-button", "n_clicks"),
    State("sku-dropdown", "value"),
    State("warehouse-code-dropdown", "value"),
    State("search-input", "value"),
    prevent_initial_call=True
)
def search_reviews(n_clicks, sku, warehouse, query):
    if not all([sku, warehouse, query]):
        raise PreventUpdate
    
    # Filter the collection based on SKU and warehouse
    filtered_docs = chroma_collection.get(
        where={"sku": sku, "warehouse_code": warehouse}
    )
    
    if not filtered_docs['ids']:
        return "No reviews found for the selected SKU and warehouse."
    
    # Create a temporary Chroma collection with filtered documents
    temp_collection = chroma_client.create_collection("temp_collection")
    temp_collection.add(
        ids=filtered_docs['ids'],
        embeddings=filtered_docs['embeddings'],
        metadatas=filtered_docs['metadatas'],
        documents=filtered_docs['documents']
    )
    
    # Create a temporary vectorstore and QA chain
    temp_vectorstore = Chroma(
        client=chroma_client,
        collection_name="temp_collection",
        embedding_function=embeddings
    )
    temp_qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        chain_type="stuff",
        retriever=temp_vectorstore.as_retriever()
    )
    
    # Run the query
    result = temp_qa_chain.run(query)
    
    # Clean up the temporary collection
    chroma_client.delete_collection("temp_collection")
    
    return result

# Add any other necessary callbacks for product research page
