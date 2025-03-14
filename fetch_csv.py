import os
import time
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from github import Github

def fetch_csv_from_pricelabs():
    """
    Fetch CSV data from PriceLabs by navigating through the website
    using browser automation with the specific XPaths provided.
    """
    print(f"[{datetime.now()}] Starting CSV fetch from PriceLabs")
    
    # Set up download directory
    download_dir = "/tmp/pricelabs_downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    # Setup headless Chrome browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Configure download behavior
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    })
    
    # Use webdriver-manager to handle driver installation
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Navigate to PriceLabs login page
        driver.get("https://pricelabs.co/signin")
        
        # Login to PriceLabs
        print(f"[{datetime.now()}] Logging in to PriceLabs")
        username = os.environ.get("PRICALABS_USERNAME")
        password = os.environ.get("PRICALABS_PASSWORD")
        
        # Wait for username field and enter credentials
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user_email"))
        )
        driver.find_element(By.ID, "user_email").send_keys(username)
        driver.find_element(By.ID, "password-field").send_keys(password)
        driver.find_element(By.XPATH, "//input[@type='submit' and @name='commit']").click()
        
        # Wait for successful login
        WebDriverWait(driver, 20).until(
            EC.url_contains("dashboard")
        )
        
        print(f"[{datetime.now()}] Successfully logged in")
        
        # Step 1: Click on the first element after login
        print(f"[{datetime.now()}] Clicking on first element")
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='mc-main']"))
        ).click()
        
        # Step 2: Click on the menu button
        print(f"[{datetime.now()}] Clicking on menu button")
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='menu-button-:r6b:']"))
        ).click()
        
        # Step 3: Click on the download CSV menu item
        print(f"[{datetime.now()}] Clicking on download CSV option")
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='menu-list-:r6b:-menuitem-:r72:']"))
        ).click()
        
        # Wait for the CSV to be generated/downloaded
        print(f"[{datetime.now()}] Waiting for download to complete...")
        time.sleep(15)  # Allow sufficient time for download
        
        # Find the most recently downloaded CSV file
        csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
        if not csv_files:
            print(f"[{datetime.now()}] No CSV files found in {download_dir}. Directory contents:")
            print(os.listdir(download_dir))
            raise Exception("No CSV file was downloaded")
            
        most_recent_csv = max(csv_files, key=os.path.getctime)
        print(f"[{datetime.now()}] Found CSV file: {most_recent_csv}")
            
        # Read the CSV file
        with open(most_recent_csv, 'r', encoding='utf-8') as file:
            csv_content = file.read()
        
        print(f"[{datetime.now()}] Successfully read CSV data")
        return csv_content
        
    except Exception as e:
        print(f"[{datetime.now()}] Error fetching CSV: {str(e)}")
        # Take a screenshot for debugging
        try:
            driver.save_screenshot("/tmp/error_screenshot.png")
            print(f"[{datetime.now()}] Saved error screenshot to /tmp/error_screenshot.png")
            # Print the current page source for debugging XPath issues
            print(f"[{datetime.now()}] Current page source:")
            print(driver.page_source[:2000] + "... (truncated)")
        except:
            pass
        return None
    finally:
        driver.quit()

def update_github_repo(csv_data):
    """Update the GitHub repository with the CSV data."""
    if not csv_data:
        print(f"[{datetime.now()}] No CSV data to commit")
        return
        
    print(f"[{datetime.now()}] Updating GitHub repository")
    
    try:
        # Get repository information from environment
        github_token = os.environ.get("GITHUB_TOKEN")  # This will be set from secrets.PAT_TOKEN
        github_repo = os.environ.get("GITHUB_REPOSITORY")
        
        print(f"[{datetime.now()}] Connecting to GitHub repository: {github_repo}")
        
        # Connect to GitHub
        g = Github(github_token)
        repo = g.get_repo(github_repo)
        
        # Create data directory if it does not exist
        try:
            repo.get_contents("data")
            print(f"[{datetime.now()}] Data directory exists")
        except:
            repo.create_file(
                "data/README.md",
                "Create data directory",
                "# CSV Data from PriceLabs\n\nThis directory contains automatically fetched CSV data."
            )
            print(f"[{datetime.now()}] Created data directory")
        
        # Format filenames
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"data/pricelabs-{today}.csv"
        
        # Create or update the daily file
        try:
            contents = repo.get_contents(filename)
            repo.update_file(
                path=filename,
                message=f"Update CSV data from PriceLabs - {today}",
                content=csv_data,
                sha=contents.sha
            )
            print(f"[{datetime.now()}] Updated {filename}")
        except:
            repo.create_file(
                path=filename,
                message=f"Add CSV data from PriceLabs - {today}",
                content=csv_data
            )
            print(f"[{datetime.now()}] Created {filename}")
        
        # Also update latest.csv
        try:
            latest = repo.get_contents("data/latest.csv")
            repo.update_file(
                path="data/latest.csv",
                message=f"Update latest CSV data - {today}",
                content=csv_data,
                sha=latest.sha
            )
            print(f"[{datetime.now()}] Updated latest.csv")
        except:
            repo.create_file(
                path="data/latest.csv",
                message=f"Add latest CSV data - {today}",
                content=csv_data
            )
            print(f"[{datetime.now()}] Created latest.csv")
            
    except Exception as e:
        print(f"[{datetime.now()}] Error updating GitHub: {str(e)}")
        print(f"Error details: {e}")

# Run the process
if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting CSV fetch and GitHub update process")
    csv_data = fetch_csv_from_pricelabs()
    update_github_repo(csv_data)
    print(f"[{datetime.now()}] Process completed")
