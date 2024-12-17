# app/utils/functions.py
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine,text
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

def load_price_data():
    """Load price data and rename columns."""
    price_df = pd.read_csv('data/price_list.csv')
    price_df.rename(columns={'item_name': 'Item', 'price': 'Takeaway Price'}, inplace=True)
    return price_df


# Function to fetch price data from the database
def fetch_price_data():
    """Fetch price list data from the database."""
    try:
        # Query to fetch item names and their corresponding prices, ensuring to get the latest price
        query = text("""
        SELECT
            ip.item_name AS Item,
            MAX(ip.price_list_rate) AS 'Takeaway Price'  -- Ensuring to get the latest price
        FROM
            `tabItem Price` ip
        GROUP BY
            ip.item_name
        ORDER BY
            ip.item_name;
        """)

        # Use pandas to execute the query and load the result into a DataFrame
        price_df = pd.read_sql(query, engine)

        # Convert the prices to integers (rounded if necessary)
        price_df['Takeaway Price'] = price_df['Takeaway Price'].round().astype(int)

        return price_df

    except Exception as err:
        st.error(f"Error fetching data: {err}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error

# Adjusted function to display the price table in Streamlit
def display_price_table():
    """Display the price table in Streamlit."""
    # Fetch the price data
    price_df = fetch_price_data()

    # Check if the dataframe is not empty
    if not price_df.empty:
        price_table_html = price_df[['Item', 'Takeaway Price']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
        st.markdown(price_table_html, unsafe_allow_html=True)
    else:
        st.error("Failed to fetch the price data.")

def filter_previous_sales_data(sales_df):
    """Filter previous sales data based on user selections."""
    sales_df['date'] = pd.to_datetime(sales_df['date'])
    date_selection = st.sidebar.radio("Select Date Range or Single Date", ("Date Range", "Single Date"))

    if date_selection == "Date Range":
        previous_date_input = st.sidebar.date_input(
            "Data Range", 
            [sales_df['date'].min().to_pydatetime(), sales_df['date'].max().to_pydatetime()]
        )
        if len(previous_date_input) == 2:
            previous_date_start, previous_date_end = previous_date_input
            previous_date_start = pd.to_datetime(previous_date_start)
            previous_date_end = pd.to_datetime(previous_date_end)
        else:
            st.error("Please select an end date.")
            return None

    if date_selection == "Single Date":
        single_date = st.sidebar.date_input(
            "Select Date", 
            sales_df['date'].min().to_pydatetime()
        )
        single_date = pd.to_datetime(single_date)

    min_date = sales_df['date'].min().strftime('%Y-%m-%d')
    max_date = sales_df['date'].max().strftime('%Y-%m-%d')
    st.warning(f"**Previous Data available from {min_date} to {max_date}.**", icon="⚠️")

    # Filters for warehouses and item groups
    previous_warehouses = sales_df['branch'].unique()
    selected_previous_warehouses = st.sidebar.multiselect("Branch", previous_warehouses)

    previous_item_groups = sales_df['item_group'].unique()
    selected_previous_item_groups = st.sidebar.multiselect("Item Group", previous_item_groups)

    filtered_items_df = sales_df[sales_df['item_group'].isin(selected_previous_item_groups)] if selected_previous_item_groups else sales_df
    previous_items = filtered_items_df['item_name'].unique()

    select_all_items = st.sidebar.checkbox("Select All Items")
    selected_previous_items = previous_items.tolist() if select_all_items else st.sidebar.multiselect("Item", previous_items)

    return previous_date_start, previous_date_end, single_date, selected_previous_warehouses, selected_previous_item_groups, selected_previous_items

def display_previous_sales_data(sales_df, date_selection, previous_date_start, previous_date_end, single_date, selected_previous_warehouses, selected_previous_item_groups, selected_previous_items):
    """Display the filtered previous sales data."""
    if selected_previous_warehouses and selected_previous_item_groups:
        if date_selection == "Date Range" and previous_date_start and previous_date_end:
            filtered_previous_df = sales_df[
                (sales_df['date'] >= previous_date_start) &
                (sales_df['date'] <= previous_date_end) &
                (sales_df['branch'].isin(selected_previous_warehouses)) &
                (sales_df['item_group'].isin(selected_previous_item_groups)) &
                (sales_df['item_name'].isin(selected_previous_items))
            ]
        elif date_selection == "Single Date":
            filtered_previous_df = sales_df[
                (sales_df['date'] == single_date) &
                (sales_df['branch'].isin(selected_previous_warehouses)) &
                (sales_df['item_group'].isin(selected_previous_item_groups)) &
                (sales_df['item_name'].isin(selected_previous_items))
            ]
        else:
            filtered_previous_df = pd.DataFrame()

        if not filtered_previous_df.empty:
            grouped_bar_fig = px.bar(filtered_previous_df, x='item_name', y='qty_sold', color='item_group', title='')
            st.plotly_chart(grouped_bar_fig)

            filtered_previous_df.rename(columns={'date': 'Date', 'item_name': 'Item', 'item_group': 'Group', 'qty_sold': 'Quantity Sold'}, inplace=True)
            table_html = filtered_previous_df[['Date', 'Item', 'Group', 'Quantity Sold', 'branch']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("No data available for the selected filters.")
    else:
        st.info("Please select all filters to view the results.")