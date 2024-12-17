import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import warnings
from sqlalchemy import create_engine,text
import os
import dotenv
import json
warnings.filterwarnings("ignore")

dotenv.load_dotenv()

# Load the branch mapping from JSON files
with open('./data/simplified_branch_mapping.json', 'r') as file:
    branch_mapping = json.load(file)

# Load the reverse branch mapping from the JSON file
with open('./data/reverse_branch_mapping.json', 'r') as file:
    reversed_branch_mapping = json.load(file)


# Access the variables
database_type = os.getenv('DATABASE_TYPE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
database_name = os.getenv('DB_NAME')
# Create the connection string
engine = create_engine(f'mysql+pymysql://{username}:{password}@{host}/{database_name}')
# Today's date and yesterday's date
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

def load_data_for_user():
    """Load data from CSV and Parquet files."""
    forecasting_df = pd.read_csv('data/new_results.csv')
    sales_data = pd.read_parquet('data/actual_sales_data.parquet')
    return forecasting_df, sales_data

def remove_items(df):
    items_to_remove = [
        "Chocolate Dreamcake ", 
        "Milk Chocolate",
        "Nutella",
        "Chunky Blend",
        "Apple Cup Pie",
        "White Chocolate ", 
        "Carrot and Cheese (Cup Cakes)",
        "All Chocolate Dreamcake -2.5 LBS",
        "Chocolate Chunk Cookie",
        "Mango Cheese Cake",
        "Blueberry Muffin",
        "Strawberry Donut",
        "Kit Kat Donut",
        "Cotton Candy Donut",
        "Matcha (Cup Cakes)",
        "Peanut Butter (Cup Cakes)",
        "Matilda Brownie",
        "Carrot Nut 2.5 LBS",
        'Malteser 2.5 LBS',
        'Nut Fusion 2.5 LBS',
        "KitKat 2.5 LBS (Cup Cakes)",
        "Peanut Butter (Cup Cakes)",
        "Matilda Brownie",
        "Carrot Nut 2.5 LBS",
        'Malteser 2.5 LBS',
        'Nut Fusion 2.5 LBS',
        'KitKat 2.5 LBS'
    ] 
    df = df[~df['item_name'].isin(items_to_remove)]
    return df

def today_forecast_and_previous_sales(forecasting_df, sales_data, selected_warehouses, selected_items,selected_item_groups):
    """Filter the forecasting and actual sales DataFrames based on selected options."""
    # Convert date columns to datetime format if needed
    forecasting_df['date'] = pd.to_datetime(forecasting_df['date'])
    sales_data['date'] = pd.to_datetime(sales_data['date'])
    sales_data = sales_data.drop_duplicates(subset=['branch', 'item_name', 'date'], keep='first')
    sales_data = remove_items(sales_data)
    forecasting_df = remove_items(forecasting_df)
    # print(forecasting_df['date'].min())
    # Filter forecast data for today's date, selected branch, and selected item
    filtered_forecasting_df = forecasting_df[
        (forecasting_df['date'] == pd.to_datetime(today)) &
        (forecasting_df['branch'].isin(selected_warehouses)) &
        (forecasting_df['item_name'].isin(selected_items))&
        (forecasting_df['item_group'].isin(selected_item_groups))
    ]

    # Filter actual sales data for only the previous day, selected branch, and selected item
    filtered_actual_df = sales_data[
        (sales_data['date'] == pd.to_datetime(yesterday)) &
        (sales_data['branch'].isin(selected_warehouses)) &
        (sales_data['item_name'].isin(selected_items))&
        (sales_data['item_group'].isin(selected_item_groups))
    ]

    return filtered_forecasting_df, filtered_actual_df



# Function to get current quantity
def get_current_quantity(selected_warehouses, selected_items):
    # Convert selected warehouse names to their corresponding warehouse codes
    warehouse_codes = [reversed_branch_mapping[branch.lower()] for branch in selected_warehouses]
# Ensure selected_items is a Python list, not a NumPy array or other type
    selected_items = selected_items.tolist() if isinstance(selected_items, np.ndarray) else selected_items

    # Then proceed as usual
    selected_items_tuple = tuple(selected_items) if selected_items else ()
    # SQL query to get the total quantities of selected items in selected warehouses
    query = text("""
    SELECT 
        sle.warehouse,
        i.item_name,
        MIN(sle.qty_after_transaction) AS total_quantity
    FROM 
        `tabStock Ledger Entry` sle
    JOIN 
        `tabItem` i ON sle.item_code = i.item_code
    WHERE 
        sle.warehouse IN :warehouses
        AND i.item_name IN :items
        AND sle.posting_date = CURDATE()
        AND sle.docstatus = 1
    GROUP BY 
        sle.warehouse, i.item_name
    """)

    # Execute the query with named parameters (use dictionaries for SQLAlchemy)
    with engine.connect() as connection:
        # Pass parameters as a dictionary
        result = connection.execute(query, {
            'warehouses': warehouse_codes,
            'items': selected_items_tuple
        })

        # Create a list to store the results
        rows = []
        for row in result:
            # Access tuple elements by index
            warehouse_code = row[0]  # First element is warehouse
            item_name = row[1]       # Second element is item_name
            total_quantity = row[2]  # Third element is total_quantity
            
            # Revert the warehouse code to the short name using the reversed branch mapping
            warehouse_name = branch_mapping.get(warehouse_code, warehouse_code)

            # Append each row as a dictionary to the list
            rows.append({
                'branch': warehouse_name,
                'item_name': item_name,
                'quantity present in branch': total_quantity
            })

    # Convert the list of rows to a pandas DataFrame
    df = pd.DataFrame(rows)

    return df


