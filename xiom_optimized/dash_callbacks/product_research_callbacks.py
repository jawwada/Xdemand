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
    
    # Create a retriever from the vectorstore
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "filter": {"$and": [{"sku": {"$eq": sku}}, {"warehouse_code": {"$eq": warehouse}}]},
            "k": 5  # Retrieve top 5 most relevant reviews
        }
    )
    
    # Retrieve relevant documents
    relevant_docs = retriever.get_relevant_documents(query)
    
    if not relevant_docs:
        return "No relevant reviews found for the given query, SKU, and warehouse_code."
    
    # Create a QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        chain_type="stuff",
        retriever=retriever
    )
    
    # Run the query
    result = qa_chain.run(query)
    
    # Format the reviews and their metadata
    reviews_output = ""
    for doc in relevant_docs:
        reviews_output += f"Review: {doc.page_content}\n"
        reviews_output += f"Metadata: {doc.metadata}\n\n"
    
    # Combine AI answer and reviews
    final_output = f"AI Answer:\n{result}\n\nRelevant Reviews:\n{reviews_output}"
    
    return final_output

# Add any other necessary callbacks for product research page