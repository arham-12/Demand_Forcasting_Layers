import pandas as pd
from sqlalchemy import create_engine
from preprocessing import DataPreprocessor
import os
import logging
import dotenv

dotenv.load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Access the variables
database_type = os.getenv('DATABASE_TYPE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
database_name = os.getenv('DB_NAME')

# Create the connection string
engine = create_engine(f'mysql+pymysql://{username}:{password}@{host}/{database_name}')

# Define the output file path
output_file = 'data/actual_sales_data.parquet'

def fetch_data(query, engine):
    """Fetch data based on a SQL query from the database."""
    logging.info(f"Executing query: {query}")
    return pd.read_sql(query, engine)

def retrieve_and_update_data(engine, output_file):
    # Determine if there's existing data and set the query accordingly
    if os.path.exists(output_file):
        existing_df = pd.read_parquet(output_file)
        max_date = existing_df['date'].max()  # Get the max date in the existing data
        logging.info(f"Max date in existing file: {max_date}")

        # Query to retrieve records from one day before the max_date
        query = f"""
            SELECT DATE(creation) as date, item_group, item_name, warehouse, SUM(qty) AS qty_sold
            FROM `tabPOS Invoice Item`
            WHERE DATE(creation) >= DATE_SUB('{max_date}', INTERVAL 1 DAY)
            GROUP BY DATE(creation), item_group, item_name, warehouse
            ORDER BY DATE(creation) ASC
        """
    else:
        logging.info("No existing file found. Fetching all data from the database.")
        # Query to retrieve all records if no local file exists
        query = """
            SELECT DATE(creation) as date, item_group, item_name, warehouse, SUM(qty) AS qty_sold
            FROM `tabPOS Invoice Item`
            GROUP BY DATE(creation), item_group, item_name, warehouse
            ORDER BY DATE(creation) ASC
        """

    # Fetch new data from the database
    new_data = fetch_data(query, engine)

    if not new_data.empty:
        # Rename columns and prepare data for merging
        new_data.rename(columns={'warehouse': 'branch'}, inplace=True)

        # Combine new data with existing data, if any, and remove duplicates
        if os.path.exists(output_file):
            combined_df = pd.concat([existing_df, new_data]).drop_duplicates(subset=['date', 'item_name', 'branch'], keep='last')
        else:
            combined_df = new_data

        # Initialize and use DataPreprocessor to preprocess the combined data
        preprocessor = DataPreprocessor()
        combined_df = preprocessor.preprocess(combined_df)

        # Save the updated combined data back to the Parquet file
        combined_df.to_parquet(output_file, engine='pyarrow', index=False)
        logging.info(f"Updated data saved to {output_file}")
    else:
        logging.info("No new data to update.")

    logging.info("Data ingestion pipeline completed successfully.")

# Call the function
retrieve_and_update_data(engine, output_file)
