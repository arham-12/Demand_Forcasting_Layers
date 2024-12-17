import pandas as pd
import streamlit as st
import json
from sqlalchemy import create_engine,text
import pandas as pd
from datetime import datetime,timedelta
import os
import dotenv

dotenv.load_dotenv()
# Access the variables
database_type = os.getenv('DATABASE_TYPE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
database_name = os.getenv('DB_NAME')

# Create the connection string
engine = create_engine(f'mysql+pymysql://{username}:{password}@{host}/{database_name}')

# Load the branch mapping from JSON files
with open('./data/simplified_branch_mapping.json', 'r') as file:
    branch_mapping = json.load(file)

# Load the reverse branch mapping from the JSON file
with open('./data/reverse_branch_mapping.json', 'r') as file:
    reversed_branch_mapping = json.load(file)





# Function to get the minimum balance with date range or a single date
def get_current_balance(selected_warehouses, selected_items, start_date=None, end_date=None):
    # Convert selected warehouse names to their corresponding warehouse codes
    warehouse_codes = [reversed_branch_mapping[branch.lower()] for branch in selected_warehouses]
    
    # Ensure selected_items is a tuple, not a list (important for SQL IN clause)
    selected_items_tuple = tuple(selected_items) if selected_items else ()

    # Handle the date logic
    if start_date and end_date:
        # If both start and end date are provided, use them in the query
        date_condition = "AND sle.posting_date BETWEEN :start_date AND :end_date"
        query_params = {
            'warehouses': warehouse_codes,
            'items': selected_items_tuple,
            'start_date': start_date,
            'end_date': end_date
        }
    elif start_date:
        # If only the start date is provided, use it in the query
        date_condition = "AND sle.posting_date = :start_date"
        query_params = {
            'warehouses': warehouse_codes,
            'items': selected_items_tuple,
            'start_date': start_date
        }
    else:
        # If no date is provided, use the current date
        date_condition = "AND sle.posting_date = CURDATE()"
        query_params = {
            'warehouses': warehouse_codes,
            'items': selected_items_tuple
        }

    # SQL query to get the minimum balance quantities for selected items in selected warehouses
    query = text(f"""
    SELECT 
        sle.warehouse,
        i.item_name,
        sle.posting_date,
        MIN(sle.qty_after_transaction) AS min_balance
    FROM 
        `tabStock Ledger Entry` sle
    JOIN 
        `tabItem` i ON sle.item_code = i.item_code
    WHERE 
        sle.warehouse IN :warehouses
        AND i.item_name IN :items
        {date_condition}
        AND sle.docstatus = 1
    GROUP BY 
        sle.warehouse, i.item_name, sle.posting_date
    ORDER BY 
        sle.posting_date ASC
    """)

    # Execute the query with named parameters (use dictionaries for SQLAlchemy)
    try:
        with engine.connect() as connection:
            result = connection.execute(query, query_params)

            # Create a list to store the results
            rows = []
            for row in result:
                # Access tuple elements by index
                warehouse_code = row[0]  # First element is warehouse
                item_name = row[1]       # Second element is item_name
                posting_date = row[2]    # Third element is posting_date
                min_balance = row[3]     # Fourth element is min_balance

                # Revert the warehouse code to the short name using the reversed branch mapping
                warehouse_name = branch_mapping.get(warehouse_code, warehouse_code)

                # Append each row as a dictionary to the list
                rows.append({
                    'branch': warehouse_name,
                    'item_name': item_name,
                    'posting_date': posting_date,
                    'balance': int(min_balance)
                })

        # Convert the list of rows to a pandas DataFrame
        df = pd.DataFrame(rows)

        return df
    except Exception as e:
        st.error(f"An error occurred while fetching the data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error


def view_available_balance(available_warehouses, available_items):
    """
    Displays the available balance based on user-selected filters.

    Args:
        available_warehouses (list): The list of available warehouses.
        available_items (list): The list of available items.
    """
    # Ask the user to select the date range
    date_selection = st.sidebar.radio("Select Date Range", ("Date Range", "Single date"))

    if date_selection == "Date Range":
        balance_date_input = st.sidebar.date_input(
            "Date Range",
            [datetime.today(), datetime.today()]
        )
        if len(balance_date_input) == 2:
            balance_start_date, balance_end_date = balance_date_input
            balance_start_date = pd.to_datetime(balance_start_date)
            balance_end_date = pd.to_datetime(balance_end_date)

            # Calculate the date difference
            date_diff = (balance_end_date - balance_start_date).days

            # If the date range exceeds 2 months (60 days), display only the message
            if date_diff > 60:
                # Adjust start date to 2 months before end date
                adjusted_start_date = balance_end_date - pd.DateOffset(months=2)
                st.warning(f"⚠️ The available date range is: {adjusted_start_date.strftime('%Y-%m-%d')} to {balance_end_date.strftime('%Y-%m-%d')} only.")
                balance_start_date = adjusted_start_date  # Update start date to 2 months before end date
            else:
                # Display the available date range
                st.warning(f"**Balance Data available from {balance_start_date.strftime('%Y-%m-%d')} to {balance_end_date.strftime('%Y-%m-%d')}**", icon="⚠️")
            
            selected_balance_warehouses = st.sidebar.multiselect("Branch", available_warehouses, default=[])
            selected_balance_items = st.sidebar.multiselect("Items", available_items, default=[])

        else:
            st.error("Please select an end date.")
            balance_start_date, balance_end_date = None, None

    elif date_selection == "Single date":
        # Ask the user to select a single date
        balance_single_date = st.sidebar.date_input("Select Single Date", datetime.today())
        balance_start_date = balance_end_date = pd.to_datetime(balance_single_date)

        selected_balance_warehouses = st.sidebar.multiselect("Branch", available_warehouses, default=[])
        selected_balance_items = st.sidebar.multiselect("Items", available_items, default=[])

    else:
        st.error("Invalid date selection")
        balance_start_date, balance_end_date = None, None

    # Fetch and display balance data if valid selections are made
    if selected_balance_warehouses and selected_balance_items and balance_start_date and balance_end_date:
        # Fetch the filtered data using the get_current_balance function
        filtered_balance_df = get_current_balance(
            selected_warehouses=selected_balance_warehouses,
            selected_items=selected_balance_items,
            start_date=balance_start_date,
            end_date=balance_end_date
        )

        if not filtered_balance_df.empty:
            # Rename columns for better display in the table
            filtered_balance_df.rename(columns={
                'item_name': 'Item',
                'branch': 'Branch',
                'posting_date': 'Date',
                'balance': 'Balance'
            }, inplace=True)

            # Show the filtered balance table
            table_html_balance = filtered_balance_df[['Item', 'Branch', 'Date', 'Balance']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
            st.markdown(table_html_balance, unsafe_allow_html=True)
        else:
            st.info("No data available for the selected filters.")
    else:
        st.info("Please select both Branch and Items to view the results.")