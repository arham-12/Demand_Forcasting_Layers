import streamlit as st
from langchain.schema import HumanMessage, AIMessage  
from model import ModelHandler


# Function to apply custom CSS styles
def apply_custom_css():
    st.markdown("""
        <style>
        /* Default styles (Light mode) */
        .title {
            color: #B09C6D;
            font-size: 2.5em;
            text-align: center;
            margin-top: 0;
        }
        .cluster-heading {
            font-size: 1.5em;
            margin-top: 1em;
            margin-bottom: 0.5em;
        }
        .sidebar .sidebar-content {
            background-color: #B09C6D;
        }
        .stButton > button {
            background-color: #B09C6D;
            color: white;
        }
        .st-info-box p {
            font-size: 1em;
        }
        /* Custom CSS for table width */
        .dataframe-font {
            width: 100%;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        td {
            text-align: justify;
            padding: 1px;
            font-size: 16px;
        }
        th {
            background-color: #B09C6D;
            color: black;
            font-size: 17px;
        }
        .prediction-count {
            font-size: 18px;
            font-weight: bold;
            color: #4A90E2;
            margin-top: 10px;
            margin-bottom: 10px;
        }
        /* Additional CSS for table text color */
        .stTable tbody td {
            color: black; /* Default text color in light mode */
        }
        .stTable thead th {
            color: black; /* Header color in light mode */
        }

        /* Dark mode styles */
        @media (prefers-color-scheme: dark) {
            .title {
                color: #B09C6D;  /* Adjust light color for dark mode */
            }
            .cluster-heading {
                color: white;
            }
            .sidebar .sidebar-content {
                background-color: #B09C6D;
            }
            .stButton > button {
                background-color: #B09C6D;
                color: white;
            }
            .st-info-box p {
                color: white;
                font-size: 1em;
            }
            table {
                color: white; /* Table color in dark mode */
            }
            td {
                color: white; /* Text color for table in dark mode */
            }
            th {
                background-color: #B09C6D;
                color: black; /* Header color in dark mode */
            }
            .prediction-count {
                font-size: 18px;
                font-weight: bold;
                color: #4A90E2;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            .stTable tbody td {
                color: white; /* Change text color for dark mode */
            }
            .stTable thead th {
                color: black; /* Change header text color for dark mode */
            }
        }
        </style>
    """, unsafe_allow_html=True)

# Function to initialize the chat model
def initialize_chat_model():
    if 'model_handler' not in st.session_state:
        with st.spinner("Please wait... Making Connection........."):
            st.session_state.model_handler = ModelHandler()
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

# Function to display demo questions
def display_demo_questions():
    if st.button("View Demo Questions"):
        with st.expander("Questions"):
            st.write("""
                - which branch had the highest total sales?
                - I want to know how many cookies were sold in 2024
                - what is average sale of belgian chocolate 2.5 lbs in 2024?
                - On which date were the most items sold?
                - which item group had the highest total sales?
                - list down the sale of three milk 2.5 lbs on 1st week of july 2024 at lake city branch
                - how many three milk 2.5 lbs were sold on 2nd july 2024 at lake city branch
                - make a report of available balance of all the items present in cookies group on 4 august 2024 at wapda town branch
                - what is the balance of three milk 2.5 lbs on 1 july 2024 at f10 markaz
                - what is the price of strawberry donut?
            """)

# Function to display chat history
def display_chat_history():
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.markdown(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.markdown(message.content)

# Function to handle user input and response
def handle_user_input():
    user_query = st.chat_input("Type a message...")
    if user_query and user_query.strip():
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        
        with st.chat_message("Human"):
            st.markdown(user_query)
        
        with st.chat_message("AI"):
            with st.spinner("Hold on... working on your query"):
                response = st.session_state.model_handler.get_response(user_query)
                st.markdown(response)
            
            st.session_state.chat_history.append(AIMessage(content=response))