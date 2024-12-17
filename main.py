# app/main.py
from utils.chatbot_functions import *
from utils.load_data_functions import *
from utils.sales_function import *
from utils.balance_functions import *
from utils.forecast_analysis_functions import *
from utils.analysis_functions import *
from utils.weakly_forecastin_functions import *
from utils.today_forecast import *
import datetime
import streamlit as st
# Main application logic
def main():
    apply_custom_css()
    
    # Sidebar image
    st.sidebar.image('data/static/Layers-Logo.png')

    # Main tab selection
    selected_tab = st.sidebar.selectbox("Select Tab", ["Today's Forecast",
        "View weekly forecasting", "View previous sales data", 
        "View available balance", "View item price", 
        "Forecasting analysis", "Chat with me"
    ])

    forecasting_df, sales_df,forecasting_all = load_data()
        # Ensure the 'date' column is in datetime format
    forecasting_df['date'] = pd.to_datetime(forecasting_df['date'], errors='coerce')
    sales_df['date'] = pd.to_datetime(sales_df['date'], errors='coerce')

    if selected_tab == "Chat with me":
        # Hide the "Layers Forecasting" title
        st.markdown('<style>h1.title {display: none;}</style>', unsafe_allow_html=True)

        initialize_chat_model()

        # Title of the chat app
        st.markdown('<h1 class="title">Chat with Layers</h1>', unsafe_allow_html=True)

        display_demo_questions()

        st.error('Please ask questions only related to "sales data", "price data" and "balance data" ')
        st.info('Please ensure your questions are specifically related to Layers. For example, you can ask: "Which branch had the highest total sales?"', icon="ℹ️")

        # Display chat history
        display_chat_history()

        # Handle user input
        handle_user_input()
    elif selected_tab == "Today's Forecast":
        st.title("Today's Forecast")
        forecasting_df, sales_data = load_data_for_user()
        analysis_warehouses = forecasting_all['branch'].unique()
        selected_analysis_warehouses = st.sidebar.multiselect("Branch", analysis_warehouses)

        analysis_item_groups = forecasting_all['item_group'].unique()
        selected_analysis_item_groups = st.sidebar.multiselect("Item Group", analysis_item_groups)

        if selected_analysis_item_groups:
            filtered_items_df = forecasting_all[forecasting_all['item_group'].isin(selected_analysis_item_groups)]
            previous_items = filtered_items_df['item_name'].unique()
        else:
            previous_items = []

        select_all_items = st.sidebar.checkbox("Select All Items")
        if select_all_items:
            selected_analysis_items = previous_items
        else:
            selected_analysis_items = st.sidebar.multiselect("Item", previous_items)

            # Ensure the condition checks if all necessary selections are made
        if (len(selected_analysis_warehouses) > 0 and 
            len(selected_analysis_item_groups) > 0 and 
            len(selected_analysis_items) > 0):
            
            print("getin current data ...")
            # Get the current quantity from the database
            current_quantity = get_current_quantity(selected_analysis_warehouses, selected_analysis_items)
            print("Current Quantity DataFrame:")
            print(current_quantity.head())
            
            # Get the filtered forecasting and actual sales data
            filtered_forecasting_df, filtered_actual_df = today_forecast_and_previous_sales(
                forecasting_df, sales_data, selected_analysis_warehouses, selected_analysis_items, selected_analysis_item_groups
            )

            # Select only relevant columns to avoid duplicates
            filtered_actual_df = filtered_actual_df[['branch', 'item_group', 'item_name', 'qty_sold', 'date', 'day', 'is_weekend', 'temperature_2m_max', 'temperature_2m_min']]
            print("Filtered Actual DataFrame:")
            print(filtered_actual_df.head())
            
            # Merge the actual and forecast data on 'branch' and 'item_name' with suffixes
            merge_df = pd.merge(filtered_actual_df, filtered_forecasting_df, on=['branch', 'item_name'], how='left', suffixes=('_actual', '_forecast'))
            print("Merged DataFrame (actual and forecast):")
            print(merge_df.head())
            
            # Check if 'prediction' exists after the merge
            if 'prediction' not in merge_df.columns:
                print("Warning: 'prediction' column not found in merged DataFrame.")
            
            # Merge with current_quantity on 'branch' and 'item name' to add quantity information
            merge_df = pd.merge(merge_df, current_quantity, how='left', on=['branch', 'item_name'])
            print("Final Merged DataFrame with Current Quantity:")
            print(merge_df.head())
            
            # Select only relevant columns to display
            display_df = pd.DataFrame({
                'date': datetime.date.today(),
                "branch": merge_df['branch'],
                "item_group": merge_df.get('item_group_actual'),  # Use .get() to avoid KeyError if column missing
                "item_name": merge_df['item_name'],
                "previous_day_sales": merge_df['qty_sold'],
                "today_forecast": merge_df.get('prediction'),  # Use .get() to avoid KeyError if column missing
                "quantity_present_in_branch": merge_df.get('quantity present in branch')  # Ensure the column name matches
            })
            display_df.drop_duplicates(inplace=True)
            
            print('displaying data ...')
            st.table(display_df)
    elif selected_tab == "View weekly forecasting":
        # Filter forecasting data
        forecasting_df = filter_forecasting_data(forecasting_df)
        # Display forecasting data
        display_filtered_data(forecasting_df)
    elif selected_tab == "View item price":
        # Load price data
        # price_df = load_price_data()
        # Display price table
        display_price_table()

    elif selected_tab == "View previous sales data":
        # Load sales data
        sales_df = load_data()[1]  # Assuming load_data returns multiple dataframes, sales_df is the second one
        previous_date_start, previous_date_end, single_date, selected_previous_warehouses, selected_previous_item_groups, selected_previous_items = filter_previous_sales_data(sales_df)
        
        # Display the previous sales data
        display_previous_sales_data(sales_df, "Date Range" if previous_date_start else "Single Date", previous_date_start, previous_date_end, single_date, selected_previous_warehouses, selected_previous_item_groups, selected_previous_items)

    elif selected_tab == "View available balance":
        # Display available balance
        view_available_balance(sales_df['branch'].unique(), sales_df['item_name'].unique())
    elif selected_tab == "Forecasting analysis":
        analysis_start_date, analysis_end_date = handle_date_selection(forecasting_all)

        analysis_warehouses = forecasting_all['branch'].unique()
        selected_analysis_warehouses = st.sidebar.multiselect("Branch", analysis_warehouses)

        analysis_item_groups = forecasting_all['item_group'].unique()
        selected_analysis_item_groups = st.sidebar.multiselect("Item Group", analysis_item_groups)

        if selected_analysis_item_groups:
            filtered_items_df = forecasting_all[forecasting_all['item_group'].isin(selected_analysis_item_groups)]
            previous_items = filtered_items_df['item_name'].unique()
        else:
            previous_items = []

        select_all_items = st.sidebar.checkbox("Select All Items")
        if select_all_items:
            selected_analysis_items = previous_items
        else:
            selected_analysis_items = st.sidebar.multiselect("Item", previous_items)

        # Check if all filters are selected before filtering data
        if (len(selected_analysis_warehouses) > 0 and 
            len(selected_analysis_item_groups) > 0 and 
            len(selected_analysis_items) > 0):
            
            filtered_forecasting_df, filtered_actual_df = filter_data(
                forecasting_df, sales_df, 
                analysis_start_date, analysis_end_date, 
                selected_analysis_warehouses, 
                selected_analysis_item_groups, 
                selected_analysis_items
            )
            

            display_results(filtered_forecasting_df, filtered_actual_df)

        else:
            st.info("Please select all filters to view the results.")

# Run the main function
if __name__ == "__main__":
    main()