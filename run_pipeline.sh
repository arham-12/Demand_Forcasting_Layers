#!/bin/bash

# Activate the conda environment
source /home/dse/miniconda3/etc/profile.d/conda.sh
conda activate chatbot

# Navigate to the directory where your scripts are located
cd /home/dse/chatbot_forecasting_layers

# Check the argument passed to the script
if [ "$1" == "daily" ]; then
    # Run daily tasks using Docker
    docker run --rm myapp
    
    # Run Streamlit app
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0

elif [ "$1" == "weekly" ]; then
    # Run weekly tasks using Docker (if applicable)
    docker run --rm myapp python3 forecasting.py

elif [ "$1" == "hourly" ]; then
    # Add the tasks you want to execute every 3 minutes here using Docker
    docker run --rm myapp python3 data_ingestion_balance.py

else
    echo "Invalid argument. Use 'daily', 'weekly', or 'hourly'."
    exit 1
fi