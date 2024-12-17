# working fine with suggestion features only for sales table, fix out of context isse, fix price table, can handle incorrect names issue, fix duplicates in the db, lower threshold

import openai
import pandas as pd
import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_groq.chat_models import ChatGroq
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.agent_toolkits import create_sql_agent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
from dotenv import load_dotenv
import requests
from fuzzywuzzy import process
import streamlit as st
from google.oauth2 import service_account
from googleapiclient import discovery
import os
load_dotenv()

api_key = os.getenv('GROQ_API_KEY')

class ModelHandler:
    def __init__(self):
        # Initialize the engine and session
        self.engine, self.session = self.init_database()
        self.db = SQLDatabase(self.engine)  # Use SQLAlchemy engine directly here
        # self.llm = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0)
        # self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        self.llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0, api_key=api_key)


        self.write_query = create_sql_query_chain(self.llm, self.db)
        self.execute_query = QuerySQLDataBaseTool(db=self.db)
        self.perspective_api_key = 'AIzaSyAwR1n7B1xhHVpc585kP5xJ8Q2n0jOAH_o'  # Update with your API key
        self.perspective_url = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'
        self.answer_prompt = PromptTemplate.from_template(
            """Given an input question, first create a syntactically correct SQLite query to run, then look at the results of the query and return the answer to the input question.
            Unless the user specifies in the question a specific number of examples to obtain, query for at most 10 results using the LIMIT clause as per SQLite. You can order the results to return the most informative data in the database.
            Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in double quotes (") to denote them as delimited identifiers.
            Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also pay attention when the user query contain item_name and branch name incorrect
            then make a global search to find the relevent item_name and branch name.

            Use the following format:

            Question: Question here
            SQLQuery: SQL Query to run
            SQLResult: Result of the SQLQuery
            Answer: Final answer here

            Only use the following tables:
            CREATE TABLE "sales" (
                "item_name" TEXT, 
                "branch" TEXT, 
                "item_group" TEXT, 
                "date" TEXT, 
                "qty_sold" INTEGER
            );

            CREATE TABLE "balance" (
                "item_name" TEXT, 
                "branch" TEXT, 
                "item_group" TEXT, 
                "date" TEXT, 
                "balance" INTEGER
            );

            CREATE TABLE "price" (
                "item_name" TEXT,
                "price" INTEGER
                "currency" TEXT
            );
            """
        )
        self.chain = (
            RunnablePassthrough.assign(query=self.write_query).assign(
                result=itemgetter("query") | self.execute_query
            )
            | self.answer_prompt | self.llm | StrOutputParser()
        )
        self.agent_executor = create_sql_agent(self.llm, db=self.db, agent_type="openai-tools", verbose=True)
        self.available_items, self.available_branches = self.fetch_items_and_branches()

        # Debugging lines to check the fetched items and branches
        print("Available Items:", self.available_items)  
        print("Available Branches:", self.available_branches)  


    def fetch_items_and_branches(self):
        # Fetch distinct item names and branches from all tables
        query_sales = "SELECT DISTINCT item_name, branch FROM sales"
        query_balance = "SELECT DISTINCT item_name, branch FROM balance"
        query_price = "SELECT DISTINCT item_name FROM price"
        
        # Combine all unique item names and branches from the sales and balance tables
        df_sales = pd.read_sql(query_sales, self.engine)
        df_balance = pd.read_sql(query_balance, self.engine)
        df_price = pd.read_sql(query_price, self.engine)

        # Combine item names from sales, balance, and price
        combined_items = pd.concat([df_sales['item_name'], df_balance['item_name'], df_price['item_name']]).unique().tolist()
        
        # Combine branches from sales and balance
        combined_branches = pd.concat([df_sales['branch'], df_balance['branch']]).unique().tolist()

        # Assign to class attributes
        self.available_items = combined_items
        self.available_branches = combined_branches

        # Debugging lines to check fetched items and branches
        print("Available Items:", self.available_items)
        print("Available Branches:", self.available_branches)

        return self.available_items, self.available_branches


    def extract_items_and_branches(self, user_query):
        found_items = []
        found_branches = []
        suggested_items = []
        suggested_branches = []
        
        # Use fuzzy matching to find similar items in the query
        for item in self.available_items:
            match = process.extractOne(user_query, [item], score_cutoff=60)
            if match:
                found_items.append(item)
            else:
                # Suggest items if the match score is above a lower threshold
                suggestion = process.extractOne(user_query, [item], score_cutoff=40)
                if suggestion:
                    suggested_items.append(suggestion[0])
        
        # Use fuzzy matching to find similar branches in the query
        for branch in self.available_branches:
            match = process.extractOne(user_query, [branch], score_cutoff=40)
            if match:
                found_branches.append(branch)
            else:
                # Suggest branches if the match score is above a lower threshold
                suggestion = process.extractOne(user_query, [branch], score_cutoff=40)
                if suggestion:
                    suggested_branches.append(suggestion[0])
        
        return found_items, found_branches, suggested_items, suggested_branches



    def check_abuse(self, text):
        params = {'key': self.perspective_api_key}
        data = {
            'comment': {'text': text},
            'requestedAttributes': {
                'TOXICITY': {}, 'SEVERE_TOXICITY': {}, 'IDENTITY_ATTACK': {},
                'INSULT': {}, 'PROFANITY': {}, 'THREAT': {}, 'SEXUALLY_EXPLICIT': {},
                'FLIRTATION': {}
            }
        }
        response = requests.post(self.perspective_url, params=params, json=data)
        result = response.json()
        scores = {attr: result.get('attributeScores', {}).get(attr, {}).get('summaryScore', {}).get('value', 0)
                  for attr in data['requestedAttributes']}
        return scores

    def preprocess_input(self, user_input):
        """Preprocess user input by stripping, lowering, and normalizing spaces."""
        return re.sub(r'\s+', ' ', user_input.lower().strip())

    def validate_input(self, user_input):
        restricted_keywords = ['DELETE', 'UPDATE', 'MODIFY', 'INSERT', 'DROP', 'ALTER', 'ADD', 'TRUNCATE', 'DEL']
        return not any(re.search(r'\b' + keyword + r'\b', user_input, re.IGNORECASE) for keyword in restricted_keywords)


    def get_response(self, user_input):
        # Preprocess the input
        processed_input = self.preprocess_input(user_input)
        
        # Validate input for dangerous SQL keywords
        if not self.validate_input(processed_input):
            return "Your query contains potentially unsafe SQL keywords."

        # Check for abusive language
        attribute_scores = self.check_abuse(processed_input)
        print("Attribute Scores:", attribute_scores)
        
        if any(score > 0.6 for score in attribute_scores.values()):
            return "Your query contains inappropriate language. Please modify your query and try again."

        # Check if the query contains potential item or branch names
        found_items = any(item in processed_input for item in self.available_items)
        found_branches = any(branch in processed_input for branch in self.available_branches)
        
        # If neither items nor branches are found, use the first logic block
        if not found_items and not found_branches:
            try:
                response = self.agent_executor.invoke({"input": processed_input})
                return response['output']
            except Exception as e:
                # Handle errors and provide a custom message
                error_message = str(e)
                if 'context length' in error_message:
                    return "Your query is too long. Please shorten it and try again."
                else:
                    return "An error occurred while processing your request. Please try again later."
        
        # If either items or branches are found, use the second logic block
        else:
            # Extract items and branches if found
            found_items, found_branches, suggested_items, suggested_branches = self.extract_items_and_branches(processed_input)

            # Prepare the response context based on found and suggested items and branches
            context = ""
            if found_items or found_branches:
                if found_items:
                    context += f"Items found in your query: {', '.join(found_items)}. "
                if found_branches:
                    context += f"Branches found in your query: {', '.join(found_branches)}. "
            else:
                # Provide suggestions if no exact matches are found
                if suggested_items or suggested_branches:
                    suggestions = []
                    if suggested_items:
                        suggestions.append(f"Did you mean these items: {', '.join(suggested_items)}?")
                    if suggested_branches:
                        suggestions.append(f"Did you mean these branches: {', '.join(suggested_branches)}?")
                    return " ".join(suggestions)
                else:
                    return "No matching items or branches found. Please check your query."

            # Add context to the user input if necessary
            enhanced_user_input = f"{context} {processed_input}".strip()

            try:
                # Debugging line to print enhanced input
                print("Enhanced User Input:", enhanced_user_input)
                
                # Process the input with the agent executor
                response = self.agent_executor.invoke({"input": enhanced_user_input})

                # Debugging line to check the response
                print("Response from agent_executor:", response)  

                return response['output']
            except Exception as e:
                # Debugging line to print exception details
                print("Error in agent_executor.invoke:", e)  
                return "Your query is too long to process. Please try simplifying your query or provide more specific details."



    def load_and_process_data(self, file_paths):
        # Read parquet files for sales and balance data
        df_list = [pd.read_parquet(file) for file in file_paths]
        return df_list

    def normalize_column(self, df, column_name):
        if column_name in df.columns:
            # Normalize column values
            df[column_name] = df[column_name].str.lower().str.strip()
            # Remove curly braces and extra spaces
            df[column_name] = df[column_name].str.replace(r'[()]', '', regex=True).str.strip()

    def apply_mappings(self, dfs):
        for df in dfs:
            self.normalize_column(df, 'item_name')
            self.normalize_column(df, 'item_group')
            # Convert 'date' columns to the required format
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

    def init_database(self):
        sqlite_db_path = 'layers.sqlite'  # Define your SQLite database path

        # Read the latest file paths
        with open('data/latest_sales_file.txt', 'r') as f:
            sales_file = f.read().strip()
        with open('data/latest_balance_file.txt', 'r') as f:
            balance_file = f.read().strip()
        with open('data/latest_price_file.txt', 'r') as f:
            price_file = f.read().strip()

        # Load and process sales and balance data
        file_paths = [sales_file, balance_file, price_file]
        sales_df, balance_df, price_df = self.load_and_process_data(file_paths)

        col = ['item_name', 'price_list_rate', 'currency']
        price_df = price_df[col]
        price_df.rename(columns={'item_name': 'item_name', 'price_list_rate': 'price', 'currency': 'currency'}, inplace=True)
        price_df['item_name'] = price_df['item_name'].str.lower()

        # Check if sales_df is loaded correctly
        print("Sales DataFrame head:", sales_df.head()) 
        # Apply mappings
        self.apply_mappings([sales_df, balance_df])

        # Further processing
        balance_df = balance_df[balance_df['voucher_type'] == 'POS Invoice']

        # Connect to SQLite database
        conn = sqlite3.connect(sqlite_db_path)
        cursor = conn.cursor()

        # Create tables if they do not exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            item_name TEXT, 
            branch TEXT, 
            item_group TEXT, 
            date TEXT, 
            qty_sold INTEGER,
            PRIMARY KEY (item_name, branch, date)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS balance (
            item_name TEXT, 
            branch TEXT, 
            item_group TEXT, 
            date TEXT, 
            balance INTEGER,
            PRIMARY KEY (item_name, branch, date)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS price (
            item_name TEXT,
            price INTEGER,
            currency TEXT,
            PRIMARY KEY (item_name)
        )
        ''')

        # Insert or update records in 'sales' table
        sales_df.to_sql('sales', conn, if_exists='replace', index=False)

        # Insert or update records in 'balance' table
        balance_df.to_sql('balance', conn, if_exists='replace', index=False)

        # Insert or update records in 'price' table
        price_df.to_sql('price', conn, if_exists='replace', index=False)

        conn.commit()
        conn.close()

        # Create a SQLAlchemy engine and session
        engine = create_engine(f'sqlite:///{sqlite_db_path}', connect_args={'check_same_thread': False}, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        return engine, session
