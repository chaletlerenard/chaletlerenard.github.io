import os
import time
import glob
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from github import Github

# ✅ Setup Logging
logging.basicConfig(
    filename='/tmp/pricelabs_script.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def log_info(message):
    logging.info(message)
    print(f"[{datetime.now()}] {message}")

def log_warning(message):
    logging.warning(message)
    print(f"[{datetime.now()}] WARNING: {message}")

def log_error(message):
    logging.error(message)
    print(f"[{datetime.now()}] ERROR: {message}")

# ✅ Validate required environment variables
def validate_env_vars(required_vars):
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise Exception(f"Missing environment variables: {', '.join(missing)}")

# ✅ Retry logic for element clicks
def retry_click(driver, xpath, retries=3, wait_between=5):
    for attempt in range(1, retries + 1):
        try:
            log_info(f"Attempt {attempt}: Clicking element {xpath}")
            element = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            log_info(f"Clicked element {xpath}")
            return
        except Exception as e:
            log_warning(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                log_info(f"Retrying in {wait_between} seconds...")
                time.sleep(wait_between)
            else:
                log_error(f"All {retries} attempts failed for {xpath}.")
                raise e

# ✅ Wait for file download
def wait_for_csv_download(download_dir, timeout=90):
    log_info(f"Waiting up to {timeout} seconds for CSV download in {download_dir}...")
    elapsed = 0
    poll_interval = 2
    while elapsed < timeout:
        csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
        if csv_files:
            latest_file = max(csv_files, key=os.path.getctime)
            log_info(f"CSV file downloaded: {latest_file}")
            return latest_file
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise Exception(f"No CSV file downloaded after {timeout} seconds!")

# ✅ Validate CSV file content
def validate_csv_file(file_path):
    log_info(f"Validating CSV file: {file_path}")
    if not os.path.exists(file_path):
        raise Exception(f"CSV file not found: {file_path}")

    size = os.path.getsize(file_path)
    if size < 100:
        raise Exception(f"CSV file too small ({size} bytes): {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if "Price" not in first_line and "price" not in first_line:
            raise Exception(f"Unexpected CSV content in first line: {first_line.strip()}")

    log_info(f"CSV file passed validation: {file_path}")

def fetch_csv_from_pricelabs():
    log_info("Starting CSV fetch from PriceLabs")

    download_dir = "/tmp/pricelabs_downloads"
    os.makedirs(download_dir, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    })

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1920, 1080)
    log_info("Set browser window size to 1920x1080")

    try:
        # Step 1: Login
        driver.get("https://pricelabs.co/signin")
        log_info("Navigating to PriceLabs login page")
        time.sleep(7)

        username = os.environ.get("PRICALABS_USERNAME")
        password = os.environ.get("PRICALABS_PASSWORD")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "user_email")))
        driver.find_element(By.ID, "user_email").send_keys(username)
        driver.find_element(By.ID, "password-field").send_keys(password)
        driver.find_element(By.XPATH, "//input[@type='submit' and @name='commit']").click()

        log_info("Submitted login form")
        time.sleep(7)

        # Step 2: Wait for dashboard to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(@class,'chakra-table')]"))
        )
        log_info("Dashboard listings table loaded")
        time.sleep(7)

        driver.save_screenshot("/tmp/after_login_screenshot.png")
        log_info("Saved post-login screenshot")

        # Step 3: Navigate to Chalet Le Renard pricing page
        target_url = "https://app.pricelabs.co/pricing?listings=1007176969711247110&pms_name=airbnb&open_calendar=true"
        driver.get(target_url)
        log_info(f"Navigated to Chalet Le Renard pricing page: {target_url}")
        time.sleep(7)

        # Step 4: Click the gear/menu button
        retry_click(driver, "//button[@qa-id='rp-ellipses-button']", retries=5, wait_between=7)

        # Step 5: Click on 'Download Prices'
        retry_click(driver, "//p[contains(text(), 'Download Prices')]", retries=5, wait_between=7)

        # Step 6: Wait for download and validate
        csv_file_path = wait_for_csv_download(download_dir, timeout=90)
        validate_csv_file(csv_file_path)

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()

        log_info("Successfully read CSV data")
        return csv_content

    except Exception as e:
        log_error(f"Error fetching CSV: {e}")
        try:
            driver.save_screenshot("/tmp/error_screenshot.png")
            log_info("Saved error screenshot")
        except Exception as screenshot_error:
            log_error(f"Screenshot capture failed: {screenshot_error}")
        return None

    finally:
        driver.quit()
        log_info("Closed browser session")

def update_github_repo(csv_data):
    if not csv_data:
        log_warning("No CSV data to commit")
        return

    log_info("Updating GitHub repository")

    try:
        github_token = os.environ.get("PAT_TOKEN")  # Ensure PAT_TOKEN is set
        github_repo = os.environ.get("GITHUB_REPOSITORY")

        g = Github(github_token)
        repo = g.get_repo(github_repo)

        log_info(f"Connected to GitHub repository: {repo.full_name}")

        branch_name = 'main'

        try:
            repo.get_contents("data", ref=branch_name)
            log_info(f"'data' directory exists in branch {branch_name}")
        except:
            log_info(f"'data' directory does not exist. Creating README.md")
            repo.create_file(
                "data/README.md",
                "Create data directory",
                "# CSV Data from PriceLabs\n\nThis directory contains automatically fetched CSV data.",
                branch=branch_name
            )

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"data/pricelabs-{today}.csv"

        try:
            contents = repo.get_contents(filename, ref=branch_name)
            log_info(f"File {filename} exists. Updating...")
            repo.update_file(
                path=filename,
                message=f"Update CSV data from PriceLabs - {today}",
                content=csv_data,
                sha=contents.sha,
                branch=branch_name
            )
        except:
            log_info(f"File {filename} does not exist. Creating it...")
            repo.create_file(
                path=filename,
                message=f"Add CSV data from PriceLabs - {today}",
                content=csv_data,
                branch=branch_name
            )

        try:
            latest = repo.get_contents("data/latest.csv", ref=branch_name)
            log_info("latest.csv exists. Updating...")
            repo.update_file(
                path="data/latest.csv",
                message=f"Update latest CSV data - {today}",
                content=csv_data,
                sha=latest.sha,
                branch=branch_name
            )
        except:
            log_info("latest.csv does not exist. Creating it...")
            repo.create_file(
                path="data/latest.csv",
                message=f"Add latest CSV data - {today}",
                content=csv_data,
                branch=branch_name
            )

        log_info("GitHub update process completed successfully")

    except Exception as e:
        log_error(f"Error updating GitHub: {e}")

if __name__ == "__main__":
    log_info("Starting CSV fetch and GitHub update process")

    try:
        validate_env_vars([
            "PRICALABS_USERNAME",
            "PRICALABS_PASSWORD",
            "PAT_TOKEN",
            "GITHUB_REPOSITORY"
        ])
        log_info("Environment variables validated")

        csv_data = fetch_csv_from_pricelabs()

        if csv_data:
            update_github_repo(csv_data)
        else:
            log_warning("CSV data is empty, skipping GitHub update")

    except Exception as e:
        log_error(f"Process failed: {e}")

    log_info("Process completed")
