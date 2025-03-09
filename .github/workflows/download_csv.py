#!/usr/bin/env python3
import os
import requests
import time
from datetime import datetime

# Get credentials from environment variables (set in GitHub secrets)
username = os.environ.get('PRICELABS_USERNAME')
password = os.environ.get('PRICELABS_PASSWORD')

# If credentials aren't available, exit
if not username or not password:
    print("Error: PriceLabs credentials not found in environment variables")
    exit(1)

# Create a session to maintain cookies
session = requests.Session()

# Step 1: Log in to PriceLabs
login_url = "https://app.pricelabs.co/login"
login_data = {
    "username": username,
    "password": password
}

try:
    # First get the login page to obtain any necessary cookies or tokens
    session.get(login_url)
    
    # Then post the login credentials
    response = session.post(login_url, data=login_data)
    
    if "Invalid credentials" in response.text:
        print("Error: Failed to log in - invalid credentials")
        exit(1)
        
    # Wait for login to process
    time.sleep(2)
    
    # Step 2: Download the CSV file
    # Note: You'll need to find the exact URL for your CSV export
    # This is just an example; you'll need to replace with the actual URL
    csv_url = "https://app.pricelabs.co/api/export/csv"
    
    # You might need to add specific parameters for your export
    params = {
        "date_from": datetime.now().strftime("%Y-%m-%d"),
        "date_to": datetime.now().strftime("%Y-%m-%d"),
        "format": "csv"
    }
    
    csv_response = session.get(csv_url, params=params)
    
    # Check if download was successful
    if csv_response.status_code != 200:
        print(f"Error: Failed to download CSV. Status code: {csv_response.status_code}")
        exit(1)
    
    # Step 3: Save the CSV file
    with open("pricelabs_data.csv", "wb") as f:
        f.write(csv_response.content)
    
    print("CSV file downloaded successfully and saved as pricelabs_data.csv")
    
except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)
