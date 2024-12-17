#!/usr/bin/env python3
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import ParameterGrid
import os
import warnings

warnings.filterwarnings('ignore')

# Check if the new_records flag indicates no new records
with open('data/status.txt', 'r') as status_file:
    new_records = int(status_file.read().strip().split('=')[1])

if new_records == 0:
    print("No new records found. Loading existing forecast results.")
    forecast_results = pd.read_csv('data/forecasting_results_8_to_8.csv')
    print(forecast_results.head())
else:
    print('Model training')
    # Load the latest parquet file
    with open('data/latest_forecasting_file.txt', 'r') as f:
        parquet_file = f.read().strip()
        df = pd.read_parquet(parquet_file)

    df['temperature_2m_max'] = df['temperature_2m_max'].fillna(df['temperature_2m_max'].mean()) 
    df['temperature_2m_min'] = df['temperature_2m_min'].fillna(df['temperature_2m_min'].mean()) 
    # Preprocess the data
    df['date'] = pd.to_datetime(df['date'])
    df['day'] = df['date'].dt.day  # Extract the 'day' feature from the date
    remove_branch = ['hayatabad', 'Victoria Saddar', 'Canal Road', 'Peshawar Cantt']
    df = df[~df['branch'].isin(remove_branch)]
    print(df['date'].max())
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
    
    dates_to_remove = [
        '2023-11-09', '2023-12-24', '2023-12-25', '2023-12-26', '2023-12-31', 
        '2024-01-01', '2024-02-08', '2024-02-14', '2024-02-26', '2024-03-23', 
        '2024-04-09', '2024-04-10', '2024-04-11', '2024-04-12', '2024-04-13', 
        '2024-05-01', '2024-05-11', '2024-05-12', '2024-06-17', '2024-06-18', 
        '2024-06-19', '2024-07-16', '2024-07-17'
    ]
    dates_to_remove = pd.to_datetime(dates_to_remove) 
    df = df[~df['date'].isin(dates_to_remove)]

    forecast_periods = 7
    all_forecast_results = pd.DataFrame()
    
    # Loop through each combination of warehouse and category
    best_mae = float('inf')
    best_params = None
    for warehouse in df['branch'].unique():
        print(f"Processing warehouse: {warehouse}")
        for category in df['item_name'].unique():
            print(f"Processing category: {category} of {warehouse}")
            category_df = df[(df['item_name'] == category) & (df['branch'] == warehouse)]
            if len(category_df) <= forecast_periods:
                continue

            train = category_df.set_index('date')[:-forecast_periods]
            test = category_df.set_index('date')[-forecast_periods:]
            train = train.drop_duplicates()

            if train['qty_sold'].dropna().shape[0] < 2:
                print(f"Skipping category '{category}' due to insufficient data.")
                continue

           
            
            # Calculate the cap as the mode of qty_sold
            cap_value = train['qty_sold'].mode().iloc[0]
            
            # Initialize the Prophet model with logistic growth
            prophet_model = Prophet(seasonality_mode='additive', growth='logistic')
            prophet_model.add_seasonality(name='weakly', period=7.0, fourier_order=3)
            prophet_model.add_country_holidays(country_name='PK')
            
            # Add regressors
            prophet_model.add_regressor('is_weekend')
            prophet_model.add_regressor('temperature_2m_max')
            prophet_model.add_regressor('temperature_2m_min')
            prophet_model.add_regressor('day')

            # Prepare data for Prophet with logistic growth cap
            train = train.reset_index().rename(columns={'date': 'ds', 'qty_sold': 'y'})
            train['cap'] = cap_value
             # Include floor value during training

            # Fit the model
            prophet_model.fit(train)

            # Create future DataFrame for prediction, including the forecast_periods
            future = prophet_model.make_future_dataframe(periods=forecast_periods)
            future = future.set_index('ds')

            # Set cap and floor for future DataFrame and merge with regressors
            future['cap'] = cap_value
            
            future = future.merge(df[['is_weekend', 'temperature_2m_max', 'temperature_2m_min', 'day']],
                                how='left', left_index=True, right_index=True)
            future = future.reset_index()

            # Fill missing regressor values
            future['is_weekend'].fillna(0, inplace=True)
            historical_mean_temp_max = df['temperature_2m_max'].mean()
            historical_mean_temp_min = df['temperature_2m_min'].mean()
            future['temperature_2m_max'].fillna(historical_mean_temp_max, inplace=True)
            future['temperature_2m_min'].fillna(historical_mean_temp_min, inplace=True)
            future['day'] = future['day'].fillna(method='ffill')
            if future['day'].isna().sum() > 0:
                future['day'] = future['day'].fillna(pd.Series((future.index % 31) + 1, index=future.index))

            # Make predictions
            prophet_forecast = prophet_model.predict(future)

            # Extract forecasted values and the uncertainty intervals
            forecasted_values = prophet_forecast['yhat'][-forecast_periods:]


            # Create the results DataFrame without the floor value
            results = pd.DataFrame({
                'date': pd.date_range(start=category_df['date'].max() + pd.Timedelta(days=1), periods=forecast_periods, freq='1D'),
                'prediction': np.round(abs(forecasted_values)).astype(int),
                'item_name': category,
                'branch': warehouse,
                'item_group': category_df['item_group'].iloc[0]
            })

            # Concatenate the results
            all_forecast_results = pd.concat([all_forecast_results, results], ignore_index=True)
            print(all_forecast_results.tail(7))
    # Save results
    csv_file = 'data/new_results.csv'
    if os.path.exists(csv_file):
        os.remove(csv_file)
        print(f"Removed old file: {csv_file}")
    all_forecast_results.to_csv(csv_file, index=False)

    print("Forecasting completed and results saved.")