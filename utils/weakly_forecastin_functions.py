import streamlit as st

def filter_forecasting_data(forecasting_df):
    """
    Filters the forecasting DataFrame based on user selections for warehouses, item groups, and items.
    
    Parameters:
        forecasting_df (DataFrame): The DataFrame containing forecasting data.
        
    Returns:
        DataFrame: The filtered DataFrame based on user selections.
    """
    # Get unique warehouses and let the user select
    warehouses = forecasting_df['branch'].unique()
    selected_warehouses = st.sidebar.multiselect("Branch", warehouses)

    # Filter by selected warehouses
    filtered_df = forecasting_df
    if selected_warehouses:
        filtered_df = filtered_df[filtered_df['branch'].isin(selected_warehouses)]

    # Get unique item groups and let the user select
    item_groups = filtered_df['item_group'].unique()
    selected_item_groups = st.sidebar.multiselect("Item Group", item_groups)

    # Filter by selected item groups
    if selected_item_groups:
        filtered_df = filtered_df[filtered_df['item_group'].isin(selected_item_groups)]

        # Add item filter
        items = filtered_df['item_name'].unique()
        selected_items = st.sidebar.multiselect("Item", items)

        # Filter by selected items
        if selected_items:
            filtered_df = filtered_df[filtered_df['item_name'].isin(selected_items)]

        return filtered_df
    else:
        st.info("Please select at least one Item Group to view the results.")
        return None


def display_filtered_data(filtered_df):
    """
    Displays the filtered DataFrame in a table format.
    
    Parameters:
        filtered_df (DataFrame): The DataFrame containing filtered data to display.
    """
    if filtered_df is not None and not filtered_df.empty:
        # Rename columns for display
        filtered_df.rename(columns={
            'date': 'Date', 
            'item_name': 'Item', 
            'item_group': 'Group', 
            'prediction': 'Model Prediction'
        }, inplace=True)

        # Display table
        table_html = filtered_df[['Date', 'Item', 'Group', 'Model Prediction', 'branch']].reset_index(drop=True).to_html(index=False, classes='dataframe-font')
        st.markdown(table_html, unsafe_allow_html=True)