# Assuming you have a function to connect to your database in common.db_constants.py
import shutil
import platform
import logging

# Workaround for the issue with the sqlite3 module
if platform.system() != "Darwin":
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb

import argostranslate.package
import argostranslate.translate
import pandas as pd
from azure.storage.blob import BlobServiceClient
from openai import OpenAI

from common.db_connection import engine, write_replace_db
from common.local_constants import AZURE_CONNECTION_STRING
from common.local_constants import region_warehouse_codes

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize OpenAI client
def get_embedding(text, model="text-embedding-3-small"):
    open_ai_client = OpenAI()
    # change text to string first
    text = str(text)
    text = text.replace("\n", " ")
    response = open_ai_client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


def install_argos_packages():
    # Download and install Argos Translate package
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
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

def translate_review():
    logger.info("Creating Amazon reviews store.")  # Log message

    # Fetch reviews from the database using Pandas
    reviews = pd.read_sql_query("""
        SELECT [Date], [im_sku] as sku, [Region], [Title], [Body], [Rating]
        FROM [dbo].[tr_amazon_reviews]    
    """, engine)  # Read directly into a DataFrame

    # Add columns for translated title and body
    reviews['Translated_Title'] = reviews.apply(lambda row: translate_review(row['Title'], row['Region'].lower(), 'en'),
                                                axis=1)
    reviews['Translated_Body'] = reviews.apply(lambda row: translate_review(row['Body'], row['Region'].lower(), 'en'),
                                               axis=1)
    write_replace_db(reviews, 'tr_amazon_reviews_translated')
def create_amazon_reviews_store():
    # Fetch reviews from the database using Pandas
    reviews = pd.read_sql_query("""
            SELECT *
            FROM [dbo].[tr_amazon_reviews_translated]    
        """, engine)
    # Save Chroma DB to SQLite file
    db_path = "amazon_reviews"
    shutil.rmtree(db_path)  # Remove the directory if it exists
    # Initialize Chroma DB client
    client = chromadb.PersistentClient(path=db_path)  # Initialize the client with settings

    # Create a new collection for Amazon reviews
    collection = client.get_or_create_collection(db_path)

    # Process and insert reviews into Chroma DB
    for index, review in reviews.iterrows():  # Iterate over DataFrame rows

        date, sku, region, title, body, rating, translated_title, translated_body = review
        warehouse_code = region_warehouse_codes.get(region, None)  # Use get to fetch the warehouse code

        # Get text embedding
        embedding = get_embedding(translated_body, model="text-embedding-3-small")

        # Add review to the collection
        collection.add(
            documents=[translated_body],
            embeddings=[embedding],
            metadatas=[{
                "date": date.strftime("%Y-%m-%d"),
                "sku": sku,
                "region": region,
                "warehouse_code": warehouse_code,
                "title": translated_title,
                "rating": rating
            }],
            ids=[str(index)]  # Add this line to provide the required 'ids' argument
        )

    zip_name = db_path
    directory_name = db_path

    # Create 'path\to\zip_file.zip'
    shutil.make_archive(zip_name, 'zip', directory_name)
    upload_to_azure_blob(f"{db_path}.zip")  # Assuming a method to save Chroma DB to SQLite


def translate_review(body, from_code, to_code):
    # Translate the review body using Argos Translate
    translated_text = argostranslate.translate.translate(body, from_code, to_code)
    logger.info(f"Translating review : {body[:100]}... from {from_code} to {to_code}.")  # Log message
    logger.info(f"Translation: {translated_text[:100]}... from {from_code} to {to_code}.")  # Log message

    return translated_text  # Return the translated text

def upload_to_azure_blob(db_path):
    # Create a BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container="amazon-reviews", blob=db_path)

    # Upload the SQLite file
    with open(db_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

