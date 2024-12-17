import pandas as pd
import plotly.express as px
from datetime import timedelta
import streamlit as st

def convert_date_format(sales_df):
    """Convert 'date' column to datetime format."""
    sales_df['date'] = pd.to_datetime(sales_df['date'])
    return sales_df

def filter_sales_data(sales_df, selected_branch, selected_item_groups):
    """Filter sales data based on selected branch and item groups."""
    filtered_data = sales_df[sales_df['branch'] == selected_branch]
    if selected_item_groups:
        filtered_data = filtered_data[filtered_data['item_group'].isin(selected_item_groups)]
    return filtered_data

def display_overall_summary(sales_df):
    """Display overall summary metrics for branches."""
    total_branches = len(sales_df['branch'].unique())
    st.markdown(f"#### Total Branches: {total_branches + 1}")

    branch_totals = sales_df.groupby('branch')['qty_sold'].sum().reset_index()
    
    # Top 5 selling branches
    top_selling_branches = branch_totals.nlargest(5, 'qty_sold').reset_index(drop=True)
    st.markdown("### Top 5 Selling Branches (Overall)")
    st.table(top_selling_branches.rename(columns={"qty_sold": "Total Quantity Sold"}))

    # Least 5 selling branches
    least_selling_branches = branch_totals.nsmallest(5, 'qty_sold').reset_index(drop=True)
    st.markdown("### Least 5 Selling Branches (Overall)")
    st.table(least_selling_branches.rename(columns={"qty_sold": "Total Quantity Sold"}))

def display_branch_summary(filtered_sales_data, selected_item_groups):
    """Display branch summary for selected item groups."""
    branch_summary = []
    for item_group in selected_item_groups:
        group_data = filtered_sales_data[filtered_sales_data['item_group'] == item_group]
        qty_sold = group_data['qty_sold'].sum()
        no_of_unique_items = group_data['item_name'].nunique()
        branch_summary.append([item_group, qty_sold, no_of_unique_items])

    branch_summary_df = pd.DataFrame(branch_summary, columns=["Item Group", "Total Quantity Sold", "Number of Unique Items"])
    st.markdown(f"### Overall Summary for {selected_item_groups}")
    st.table(branch_summary_df)

def daily_analysis(filtered_sales_data):
    """Perform daily analysis and display results."""
    selected_date = st.sidebar.date_input("Select Date", filtered_sales_data['date'].min())
    daily_data = filtered_sales_data[filtered_sales_data['date'] == pd.Timestamp(selected_date)]
    
    if not daily_data.empty:
        st.markdown(f"### Sales Data for {selected_date.strftime('%Y-%m-%d')}")
        daily_sales_fig = px.bar(daily_data, x='item_name', y='qty_sold', color='item_group', title='Daily Sales', barmode="group")
        st.plotly_chart(daily_sales_fig)
        
        st.markdown("#### Top 5 Selling Items")
        top_items = daily_data.nlargest(5, 'qty_sold').reset_index(drop=True)
        st.table(top_items[['item_name', "item_group", 'qty_sold']])
        
        st.markdown("#### Least 5 Selling Items")
        least_items = daily_data.nsmallest(5, 'qty_sold').reset_index(drop=True)
        st.table(least_items[['item_name', "item_group", 'qty_sold']])
    else:
        st.info(f"No sales data available for {selected_date.strftime('%Y-%m-%d')}.")

def weekly_analysis(filtered_sales_data):
    """Perform weekly analysis and display results."""
    selected_week = st.sidebar.date_input("Select Week", filtered_sales_data['date'].min())
    start_date = pd.Timestamp(selected_week) - timedelta(days=pd.Timestamp(selected_week).weekday())
    end_date = start_date + timedelta(days=6)
    weekly_data = filtered_sales_data[(filtered_sales_data['date'] >= start_date) & (filtered_sales_data['date'] <= end_date)]
    
    if not weekly_data.empty:
        st.markdown(f"### Sales Data for Week of {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        weekly_sales_fig = px.bar(weekly_data, x='item_name', y='qty_sold', color='item_group', title='Weekly Sales')
        st.plotly_chart(weekly_sales_fig)
        
        st.markdown("#### Top 5 Selling Items")
        top_items = weekly_data.groupby('item_name')['qty_sold'].sum().nlargest(5).reset_index()
        st.table(top_items)
        
        st.markdown("#### Least 5 Selling Items")
        least_items = weekly_data.groupby('item_name')['qty_sold'].sum().nsmallest(5).reset_index()
        st.table(least_items)
    else:
        st.info(f"No sales data available for the week of {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.")

def monthly_analysis(filtered_sales_data):
    """Perform monthly analysis and display results."""
    selected_date = st.sidebar.date_input("Select Date", filtered_sales_data['date'].min())
    selected_month = selected_date.month
    selected_year = selected_date.year

    monthly_data = filtered_sales_data[(filtered_sales_data['date'].dt.month == selected_month) &
                                        (filtered_sales_data['date'].dt.year == selected_year)]

    if not monthly_data.empty:
        st.markdown(f"### Sales Data for {selected_date.strftime('%B %Y')}")
        monthly_sales_fig = px.bar(monthly_data, x='item_name', y='qty_sold', color='item_group', title='Monthly Sales')
        st.plotly_chart(monthly_sales_fig)

        st.markdown("#### Top 5 Selling Items in the Month")
        top_monthly_items = monthly_data.groupby('item_name')['qty_sold'].sum().nlargest(5).reset_index()
        st.table(top_monthly_items)
        
        st.markdown("#### Least 5 Selling Items in the Month")
        least_monthly_items = monthly_data.groupby('item_name')['qty_sold'].sum().nsmallest(5).reset_index()
        st.table(least_monthly_items)
    else:
        st.info(f"No sales data available for {selected_date.strftime('%B %Y')}.")

def sales_analysis(sales_df):
    """Main function to perform sales analysis."""
    st.markdown('<h2 class="title">Sales Analysis</h2>', unsafe_allow_html=True)
    sales_df = convert_date_format(sales_df)

    # Sidebar filters
    branches = sales_df['branch'].unique()
    selected_branch = st.sidebar.selectbox("Select Branch", ['Select'] + list(branches))

    if selected_branch != 'Select':
        filtered_sales_data = filter_sales_data(sales_df, selected_branch, st.sidebar.multiselect("Select Item Group", sales_df[sales_df['branch'] == selected_branch]['item_group'].unique()))
        
        if filtered_sales_data.empty:
            st.info("Please select at least one Item Group to view the analysis.")
            return

        display_overall_summary(sales_df)
        display_branch_summary(filtered_sales_data, st.sidebar.multiselect("Select Item Group", filtered_sales_data['item_group'].unique()))

        analysis_type = st.sidebar.radio("Select Analysis Type", ["Daily", "Weekly", "Monthly"])

        if analysis_type == "Daily":
            daily_analysis(filtered_sales_data)
        elif analysis_type == "Weekly":
            weekly_analysis(filtered_sales_data)
        elif analysis_type == "Monthly":
            monthly_analysis(filtered_sales_data)
    else:
        st.info("Please select a branch to view the analysis.")
