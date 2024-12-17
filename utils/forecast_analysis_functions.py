import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
def handle_date_selection(forecasting_all):
    """Handle the date selection logic."""
    date_selection = st.sidebar.radio("Select Date Option", ("Date Range", "Single Date"))

    if date_selection == "Date Range":
        dates = st.sidebar.date_input(
            "Date Range", 
            [forecasting_all['date'].min().to_pydatetime(), forecasting_all['date'].max().to_pydatetime()]
        )

        if len(dates) == 2:
            analysis_start_date, analysis_end_date = pd.to_datetime(dates)
        else:
            st.warning("Please select both start and end dates.")
            analysis_start_date, analysis_end_date = None, None

    elif date_selection == "Single Date":
        single_date = st.sidebar.date_input(
            "Select Date", 
            forecasting_all['date'].min().to_pydatetime()
        )
        analysis_start_date = analysis_end_date = pd.to_datetime(single_date)

    # Display the available date range
    min_date = forecasting_all['date'].min().strftime('%Y-%m-%d')
    max_date = forecasting_all['date'].max().strftime('%Y-%m-%d')
    st.warning(f"**Forecasting Data available from {min_date} to {max_date}.**", icon="⚠️")

    return analysis_start_date, analysis_end_date


def filter_data(forecasting_df, sales_df, analysis_start_date, analysis_end_date, 
                selected_analysis_warehouses, selected_analysis_item_groups, selected_analysis_items):
    """Filter the forecasting and actual sales DataFrames based on selected options."""
    filtered_forecasting_df = forecasting_df[
        (forecasting_df['date'] >= analysis_start_date) &
        (forecasting_df['date'] <= analysis_end_date) &
        (forecasting_df['branch'].isin(selected_analysis_warehouses)) &
        (forecasting_df['item_group'].isin(selected_analysis_item_groups)) &
        (forecasting_df['item_name'].isin(selected_analysis_items))
    ]

    filtered_actual_df = sales_df[
        (sales_df['date'] >= analysis_start_date) &
        (sales_df['date'] <= analysis_end_date) &
        (sales_df['branch'].isin(selected_analysis_warehouses)) &
        (sales_df['item_group'].isin(selected_analysis_item_groups)) &
        (sales_df['item_name'].isin(selected_analysis_items))
    ]
    print(filtered_forecasting_df.shape)
            
    print(filtered_actual_df.shape)

    return filtered_forecasting_df, filtered_actual_df


def display_results(filtered_forecasting_df, filtered_actual_df):
    """Display the results including charts and tables."""
    # Ensure the 'date' column is in datetime format
    filtered_forecasting_df['date'] = pd.to_datetime(filtered_forecasting_df['date'])
    filtered_actual_df['date'] = pd.to_datetime(filtered_actual_df['date'])
    filtered_actual_df.dropna(subset=['qty_sold'], inplace=True)
    filtered_forecasting_df.dropna(subset=['prediction'], inplace=True)
    # Merging the dataframes on date, item_name, branch, and item_group
    merged_df = pd.merge(filtered_forecasting_df, filtered_actual_df, 
                         on=['date', 'item_name', 'branch', 'item_group'], how='inner')
    merged_df = merged_df.drop_duplicates()
    print(merged_df.shape)
    def calculate_absolute_error(row):
        return abs(row['qty_sold'] - row['prediction'])

    # Calculate Absolute Error for each row
    merged_df['Absolute Error'] = merged_df.apply(calculate_absolute_error, axis=1)

    # Calculate Naive Forecast Errors
    merged_df['Naive Error'] = merged_df['qty_sold'].diff().abs()  # Absolute difference from previous quantity sold

    # Calculate Mean Absolute Error (MAE) of the model
    mae_value = merged_df['Absolute Error'].mean()

    # Calculate Mean Absolute Error (MAE) of the naive forecast (ignoring the first row with NaN)
    naive_mae = merged_df['Naive Error'][1:].mean()

    # Calculate Mean Absolute Scaled Error (MASE)
    mase_value = mae_value / naive_mae if naive_mae != 0 else np.nan  # Handle division by zero

    # Calculate Relative Absolute Error (RAE) for each row
    merged_df['Relative Absolute Error'] = (merged_df['Absolute Error'] / merged_df['qty_sold'].replace(0, np.nan)) * 100

    # Calculate mean and standard deviation of Absolute Error for Z-Score normalization
    mean_absolute_error = merged_df['Absolute Error'].mean()
    std_absolute_error = merged_df['Absolute Error'].std()

    # Calculate Z-Score Normalization
    merged_df['Z-Score Error'] = (merged_df['Absolute Error'] - mean_absolute_error) / std_absolute_error

    # Rename columns for consistency
    merged_df.rename(columns={
        'date': 'Date',
        'item_name': 'Item',
        'item_group': 'Group',
        'qty_sold': 'Quantity Sold',
        'prediction': 'Model Prediction',
    }, inplace=True)

    # Display Mean Absolute Scaled Error (MASE) in Streamlit
    st.markdown(f"### Mean Absolute Scaled Error (MASE) for the dataset: {mase_value:.2f}")

    # Display Actual Quantity Sold vs. Model Prediction
    st.markdown("### Actual Quantity Sold vs. Model Prediction")
    bar_plot_df = merged_df[['Date', 'Quantity Sold', 'Model Prediction']]
    bar_plot_df = bar_plot_df.melt(id_vars='Date', value_vars=['Quantity Sold', 'Model Prediction'], 
                                    var_name='Metric', value_name='Value')
    bar_plot_fig = px.bar(bar_plot_df, x='Date', y='Value', color='Metric', 
                        barmode='group', title='Actual Quantity Sold vs. Model Prediction')
    st.plotly_chart(bar_plot_fig)

    # Categorize Z-Score Error into different ranges
    z_score_less_than_neg_1_df = merged_df[merged_df['Z-Score Error'] < -1]
    z_score_between_neg_1_and_1_df = merged_df[(merged_df['Z-Score Error'] >= -1) & (merged_df['Z-Score Error'] <= 1)]
    z_score_greater_than_1_df = merged_df[merged_df['Z-Score Error'] > 1]

    # Display the results
    print(f"Z-Score < -1 DataFrame: {z_score_less_than_neg_1_df.shape}")
    print(f"Z-Score between -1 and 1 DataFrame: {z_score_between_neg_1_and_1_df.shape}")
    print(f"Z-Score > 1 DataFrame: {z_score_greater_than_1_df.shape}")

    # Display tables based on Z-Score
    st.markdown('<h1 class="cluster-heading">Z-Score < -1</h1>', unsafe_allow_html=True)
    st.subheader(f"Count of Z-Score < -1: {len(z_score_less_than_neg_1_df)}")
    table_html_less_than_neg_1 = z_score_less_than_neg_1_df[['Date', 'Item', 'Group', 'Quantity Sold', 'Model Prediction', 'Z-Score Error', 'branch']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
    st.markdown(table_html_less_than_neg_1, unsafe_allow_html=True)

    st.markdown('<h1 class="cluster-heading">Z-Score between -1 and 1</h1>', unsafe_allow_html=True)
    st.subheader(f"Count of Z-Score between -1 and 1: {len(z_score_between_neg_1_and_1_df)}")
    table_html_between_neg_1_and_1 = z_score_between_neg_1_and_1_df[['Date', 'Item', 'Group', 'Quantity Sold', 'Model Prediction', 'Z-Score Error', 'branch']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
    st.markdown(table_html_between_neg_1_and_1, unsafe_allow_html=True)

    st.markdown('<h1 class="cluster-heading">Z-Score > 1</h1>', unsafe_allow_html=True)
    st.subheader(f"Count of Z-Score > 1: {len(z_score_greater_than_1_df)}")
    table_html_greater_than_1 = z_score_greater_than_1_df[['Date', 'Item', 'Group', 'Quantity Sold', 'Model Prediction', 'Z-Score Error', 'branch']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
    st.markdown(table_html_greater_than_1, unsafe_allow_html=True)