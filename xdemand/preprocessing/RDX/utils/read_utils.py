import csv
import re
from io import StringIO

import pandas as pd


def replace_month(date_str, month):
    parts = date_str.split(' ')
    parts[1] = month
    return ' '.join(parts)


def get_region_from_blob_name(blob_name):
    match = re.search(r'\s(.*?)\.(?:csv|xlsx)', os.path.basename(blob_name))
    return match.group(1) if match else None


def clean_data(data):
    lines = data.splitlines()
    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    for index, line in enumerate(lines):
        if line[0].isdigit() or line[:3] in month_names or line[1:4] in month_names or line[1].isdigit():
            return '\n'.join(lines[index-1:])
    return None
from datetime import datetime
import pytz

def convert_to_utc(date_string):
    formats = [
        "%Y-%m-%d %H:%M:%S %Z",
        "%b. %d, %Y %I:%M:%S %p. %Z"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_string, fmt)
            dt_utc = dt.astimezone(pytz.UTC)
            return dt_utc
        except ValueError:
            continue
    return None

# Process CSV files
def process_csv_file(blob):
    print(f"Processing CSV file: {blob.name}")

    # Extract year and month from the blob name
    parts = blob.name.split('/')
    year = int(parts[2])
    month = parts[-2]
    print(year)
    print(month)

    # Read the file into a list of lines
    with open(file_path, 'r') as file:
        data = file.readlines()

    if data.startswith(b'\xef\xbb\xbf'):  # Check if data starts with BOM
        encoding = 'utf-8-sig'
    else:
        encoding = 'utf-8'
    try:
        data = blob_client.download_blob().content_as_text(encoding=encoding)
    except UnicodeDecodeError:
        print(f"Error reading blob as utf-8: {blob.name}, trying with 'ISO-8859-1'")
        data = blob_client.download_blob().content_as_text(encoding='ISO-8859-1')
    print(f"Reading blob: {blob.name}")

    data = clean_data(data)
    if data == None:
        return None
    # Read the data into a DataFrame
    sniffer = csv.Sniffer()
    delimiter = sniffer.sniff(data).delimiter
    print(f"Reading blob: {blob.name}")

    # Read the data into a DataFrame
    df = pd.read_csv(StringIO(data), delimiter=delimiter, header=0)
    df['year'] = year
    df['month'] = month
    # Replace the month string in the date/time column
    date_time_col = df.columns[0]
    df = df.dropna(subset=[date_time_col])

    # Extract region from the blob name and set it as an additional column value
    region = get_region_from_blob_name(blob.name)
    df['region'] = region

    #df[date_time_col] = pd.to_datetime(df[date_time_col], utc=True)
    try:
        df[date_time_col] = pd.to_datetime(df[date_time_col], utc=True)
    except ValueError:
        df[date_time_col] = df[date_time_col].apply(convert_to_utc)
        df[date_time_col] = pd.to_datetime(df[date_time_col], utc=True)

    print(f"Read blob: {blob.name}")
    print(df.head(2))
    return df


def process_excel_file(blob, container_client):
    blob_client = container_client.get_blob_client(blob)
    data = blob_client.download_blob()
    sheet_name='MonthlyTransactions'
    # Load the Excel file
    print(f"Reading blob: {blob.name}")

    xls = pd.ExcelFile(data)

    # Get the sheet names
    sheet_names = xls.sheet_names

    # Print sheet names
    print(sheet_names)

    # Assuming you want to load a sheet with the name 'desired_sheet_name'
    if sheet_name in sheet_names:
        df = pd.read_excel(xls, sheet_name)
    else:
        print("Sheet with the desired name not found.")
    # Implement th e processing for Excel files here
    pass

def read_blob_into_dataframe(file_name,):
    if '.DS_Store' in blob:  # Skip files with .DS_Store in their name
        return None

    folder_name = "Amazon Sales DATA"
    if folder_name not in file_name:  # Only process files within the specified folder
        return None

    if file_name.endswith('.csv'):
        return process_csv_file(file_name)
    elif file_name.endswith('.xlsx'):
        return process_excel_file(file_name)
    else:
        return None
# -*- coding: utf-8 -*-

