# Assuming you have a function to connect to your database in common.db_constants.py
from common.db_connection import engine
from chromadb import Client  # Make sure to install chromadb
import argostranslate.package
import argostranslate.translate
import sqlite3
from azure.storage.blob import BlobServiceClient
from common.local_constants import AZURE_CONNECTION_STRING, BLOB_NAME
from common.local_constants import region_warehouse_codes
import pandas as pd  # Add this import at the top
from common.logger_ import logger  # Add this import at the top

# Download and install Argos Translate package
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()

def install_argos_packages():
    logger.info("Starting installation of Argos Translate packages.")  # Log message
    # Fetch unique regions from the database
    unique_regions_query = pd.read_sql_query("""
        SELECT DISTINCT [Region]
        FROM [dbo].[tr_amazon_reviews]
        WHERE [Region] IS NOT NULL
    """, engine)  # Execute the query to get unique regions

    unique_regions = set(unique_regions_query['Region'].str.lower()) - {'en'}  # Exclude 'english'
    
    for region in unique_regions:
        logger.info(f"Installing package for region: {region}")  # Log message
        from_code = region  # Set from_code based on the region
        to_code = 'en'  # Assuming English is the target language
        available_packages = argostranslate.package.get_available_packages()
        package_to_install = next(
            filter(
                lambda x: x.from_code == from_code and x.to_code == to_code, available_packages
            ),
            None
        )
        if package_to_install:
            argostranslate.package.install_from_path(package_to_install.download())

def create_amazon_reviews_store():
    logger.info("Creating Amazon reviews store.")  # Log message

    # Fetch reviews from the database using Pandas
    reviews = pd.read_sql_query("""
        SELECT TOP 1000 [Date], [im_sku], [Region], [Title], [Body], [Rating]
        FROM [dbo].[tr_amazon_reviews]
    """, engine)  # Read directly into a DataFrame

    # Install Argos Translate packages for unique regions
    install_argos_packages()

    # Initialize Chroma DB client
    client = Client()

    # Create a new collection for Amazon reviews
    collection = client.create_collection("amazon_reviews")

    # Process and insert reviews into Chroma DB
    for index, review in reviews.iterrows():  # Iterate over DataFrame rows
        
        date, im_sku, region, title, body, rating = review
        warehouse_code = region_warehouse_codes.get(region, None)  # Use get to fetch the warehouse code
        
        # Set from_code and to_code based on the region
        from_code = region.lower()  # Assuming English is the source language
        to_code = 'en' # Use the region field as the target language code

        logger.info(f"Translating review from {from_code} to {to_code}.")  # Log message
        # Translate the review body
        translated_body = translate_review(body, from_code, to_code)  # Pass codes to translation
        # Add review to the collection
        collection.add(
            documents=[translated_body],
            metadatas=[{
                "date": date.strftime("%Y-%m-%d"),
                "im_sku": im_sku,
                "region": region,
                "warehouse_code": warehouse_code,
                "title": title,
                "rating": rating
            }],
            ids=[str(index)]  # Add this line to provide the required 'ids' argument
        )

    # Save Chroma DB to SQLite file
    sqlite_file_path = "amazon_reviews.db"
    client.save_to_sqlite(sqlite_file_path)  # Assuming a method to save Chroma DB to SQLite

    # Upload SQLite file to Azure Blob Storage
    upload_to_azure_blob(sqlite_file_path)

    # Close the database connection
    conn.close()

def translate_review(body, from_code, to_code):
    logger.info(f"Translating review body: {body[:30]}... from {from_code} to {to_code}.")  # Log message
    # Translate the review body using Argos Translate
    translated_text = argostranslate.translate.translate(body, from_code, to_code)
    return translated_text  # Return the translated text

def upload_to_azure_blob(file_path):
    # Create a BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container="your-container-name", blob=BLOB_NAME)

    # Upload the SQLite file
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

if __name__ == "__main__":
    install_argos_packages()
    create_amazon_reviews_store()