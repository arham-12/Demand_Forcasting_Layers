import pandas as pd
import streamlit as st

def load_data():
    """Load data from CSV and Parquet files."""
    forecasting_df = pd.read_csv('data/new_results.csv')
    forecasting_all = pd.read_parquet('data/actual_sales_data.parquet')
 

    # Load previous date data
    with open('data/latest_sales_file.txt', 'r') as file:
        sales_file_path = file.read().strip()
    sales_df = pd.read_parquet(sales_file_path)

    # with open('data/latest_balance_file.txt', 'r') as file:
    #     balance_file_path = file.read().strip()
    # balance_df = pd.read_parquet(balance_file_path)
    # balance_df = balance_df[balance_df['voucher_type'] == 'POS Invoice']

    # Convert date format in previous date data
    sales_df['date'] = pd.to_datetime(sales_df['date']).dt.strftime('%Y-%m-%d')

    return forecasting_df, sales_df,forecasting_all

