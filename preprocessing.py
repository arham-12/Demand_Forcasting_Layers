import pandas as pd
import json
import requests
from sklearn.preprocessing import LabelEncoder

class DataPreprocessor:
    def __init__(self, branch_mapping_file='data/simplified_branch_mapping.json', 
                 branch_info_file='data/branch_info.json'):
        # Load JSON files once to avoid redundant I/O
        with open(branch_mapping_file, 'r') as f:
            self.branch_mappings = json.load(f)

        with open(branch_info_file, 'r') as f:
            self.branch_info = json.load(f)

    def sort_by_date(self, df):
        """Sort the DataFrame by date in descending order."""
        if df is None:
            return None
        return df.sort_values(by='date', ascending=True)




    def group_by_and_sum_daily_quantities(self, df):
        """Group by and sum daily quantities, then return the processed DataFrame."""
        if df is None:
            return None
        df['date'] = pd.to_datetime(df['date'])
        # Sum 'qty_sold' daily by 'branch' and 'item_name'
        df['date'] = df['date'].dt.date  # Convert datetime to just date for grouping
        daily_sum_df = (
            df.groupby(['branch', 'item_name', 'date'])
            .agg({'qty_sold': 'sum'})
            .reset_index()
            .rename(columns={'qty_sold': 'qty_sold_daily'})
        )

        # Merge back to the main DataFrame
        df = pd.merge(df, daily_sum_df, on=['branch', 'item_name', 'date'], how='left')
        df['qty_sold'] = df['qty_sold_daily']
        df.drop(columns=['qty_sold_daily'], inplace=True)

        # Avoid duplicated data
        df = df.drop_duplicates()

        return df


    def replace_branch_names(self, df):
        """Replace branch names with simplified names."""
        df['branch'] = df['branch'].replace(self.branch_mappings)
        return df

    def add_branch_info(self, df):
        """Add city, latitude, and longitude information based on branch mapping."""
        df['city'] = df['branch'].map(lambda x: self.branch_info.get(x, {}).get('city'))
        df['latitude'] = df['branch'].map(lambda x: self.branch_info.get(x, {}).get('latitude'))
        df['longitude'] = df['branch'].map(lambda x: self.branch_info.get(x, {}).get('longitude'))
        print(df.head())
        return df

    def add_day_col(self, df):
        df['date'] = pd.to_datetime(df['date'])

        df['day'] = df['date'].dt.day_name()
        return df
    
    def add_is_weekend_col(self, df):
        """Add a column to indicate whether the date falls on a weekend."""
        df['date'] = pd.to_datetime(df['date'])
        df['is_weekend'] = df['date'].dt.dayofweek >= 5  # Saturday and Sunday are 5 and 6
        return df

    def add_temp_cols(self, df):
        """Fetch temperature data for unique latitude and longitude pairs and add it to the DataFrame."""
        # Convert the 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'])

        # Step 2: Fetch unique dates from the sales data
        unique_dates = df['date'].dt.strftime('%Y-%m-%d').tolist()

        # Step 3: Get unique latitude and longitude pairs
        unique_locations = df[['latitude', 'longitude']].drop_duplicates()

        # Prepare a DataFrame to hold temperature data
        temp_data = pd.DataFrame()

        # Fetch temperature data for each unique location
        for _, location in unique_locations.iterrows():
            latitude = location['latitude']
            longitude = location['longitude']

            # Check if latitude and longitude are valid
            if pd.isna(latitude) or pd.isna(longitude):
                print(f"Skipping invalid location: {latitude}, {longitude}")
                continue

            start_date = min(unique_dates)
            end_date = max(unique_dates)

            url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,temperature_2m_min&timezone=Asia/Karachi"

            # Fetch the temperature data
            response = requests.get(url)
            temperature_data = response.json()
            print(f"Temperature data fetched for location: {latitude}, {longitude}")
            print(f"Response: {temperature_data}")

            if 'daily' not in temperature_data:
                print(f"No daily temperature data for location: {latitude}, {longitude}")
                continue  # Skip to the next location if no data is returned

            # Create a DataFrame from the temperature data
            temp_df = pd.DataFrame(temperature_data['daily'])

            # Add latitude and longitude to the temperature DataFrame
            temp_df['latitude'] = latitude
            temp_df['longitude'] = longitude

            # Rename 'time' to 'date' for merging
            temp_df = temp_df.rename(columns={'time': 'date'})

            # Convert 'date' in the temperature DataFrame to datetime
            temp_df['date'] = pd.to_datetime(temp_df['date'])

            # Append to the temp_data DataFrame
            temp_data = pd.concat([temp_data, temp_df], ignore_index=True)

        # Step 4: Drop duplicate temperature columns if they exist in the original DataFrame
        df = df.drop(columns=['temperature_2m_max', 'temperature_2m_min'], errors='ignore')

        # Merge the sales data with the temperature data using 'date' and location
        merged_data = pd.merge(df, temp_data, on=['date', 'latitude', 'longitude'], how='left')

        # Print the merged DataFrame
        print(merged_data)

        return merged_data

    def remove_uncessary_cols(self, df):
        """Remove unnecessary columns."""
        df = df.drop(columns=['city',	'latitude'	,'longitude'])
        return df

    def encode_categorical_col(self, df):
        """Encode categorical columns using one-hot encoding."""
        encoder = LabelEncoder()
        df['day'] = encoder.fit_transform(df['day'])
        return df


    def fill_null_values(self, df):
        """fill null values."""
        columns_to_fill = ['temperature_2m_max', 'temperature_2m_min']  # Specify the columns you want to fill with the mean

        for col in columns_to_fill:
            # Fill NaN values in the specified column with the mean of that column
            df[col] = df[col].fillna(df[col].mean())

        return df
    def preprocess(self, df):
        """Preprocess the DataFrame by applying all transformations."""
        # Ensure 'date' column is in datetime format
        df['date'] = pd.to_datetime(df['date'])

        # Sort by date in descending order
        df = self.sort_by_date(df)
        # Replace branch names
        df = self.replace_branch_names(df)
        # group by and sum daily quantities
        # df = self.group_by_and_sum_daily_quantities(df)


        # Add a new column with the day of the week
        df = self.add_day_col(df)

        # add is weekend column
        df = self.add_is_weekend_col(df)

        # Process the data and add branch info
        df = self.add_branch_info(df)

        # Add temperature data
        df =  self.add_temp_cols(df)
        # remove unnessory cols 
        df = self.remove_uncessary_cols(df)
        # encode categorical colums
        df = self.encode_categorical_col(df)

        # fill null values
        df = self.fill_null_values(df)
        return df