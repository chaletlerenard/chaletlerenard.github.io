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
    print(f"[{datetime.now()}] Starting CSV fetch from PriceLabs")

    download_dir = "/tmp/pricelabs_downloads"
    os.makedirs(download_dir, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Comment out for debugging (optional)
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

    # ✅ Set browser window size to ensure UI is fully visible
    driver.set_window_size(1920, 1080)
    print(f"[{datetime.now()}] Set browser window size to 1920x1080")

    try:
        # Step 1: Login
        driver.get("https://pricelabs.co/signin")
        print(f"[{datetime.now()}] Loading PriceLabs login page...")
        time.sleep(7)

        print(f"[{datetime.now()}] Logging in to PriceLabs")
        username = os.environ.get("PRICALABS_USERNAME")
        password = os.environ.get("PRICALABS_PASSWORD")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user_email"))
        )
        driver.find_element(By.ID, "user_email").send_keys(username)
        driver.find_element(By.ID, "password-field").send_keys(password)
        driver.find_element(By.XPATH, "//input[@type='submit' and @name='commit']").click()

        print(f"[{datetime.now()}] Submitted login form")
        time.sleep(7)

        # Step 2: Wait for dashboard listings table to load
        print(f"[{datetime.now()}] Waiting for dashboard listings table to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(@class,'chakra-table')]"))
        )
        print(f"[{datetime.now()}] Dashboard listings table loaded")
        time.sleep(7)

        # Optional: Screenshot after login
        driver.save_screenshot("/tmp/after_login_screenshot.png")
        print(f"[{datetime.now()}] Saved post-login screenshot to /tmp/after_login_screenshot.png")

        # Step 3: Navigate directly to Chalet Le Renard page
        target_url = "https://app.pricelabs.co/pricing?listings=1007176969711247110&pms_name=airbnb&open_calendar=true"
        print(f"[{datetime.now()}] Navigating directly to Chalet Le Renard page: {target_url}")
        driver.get(target_url)

        print(f"[{datetime.now()}] Waiting 7 seconds for page to load...")
        time.sleep(7)

        # Step 4: Wait for Chalet Le Renard pricing page to load
        print(f"[{datetime.now()}] Waiting for Chalet Le Renard page to be ready...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//button[@qa-id='rp-ellipses-button']"))
        )
        print(f"[{datetime.now()}] Chalet Le Renard page is ready")
        time.sleep(7)

        # Step 5: Click the gear/menu button
        print(f"[{datetime.now()}] Clicking the gear/menu button...")
        menu_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@qa-id='rp-ellipses-button']"))
        )
        menu_button.click()
        print(f"[{datetime.now()}] Clicked the gear/menu button")
        time.sleep(7)

        # Step 6: Click on 'Download Prices'
        print(f"[{datetime.now()}] Waiting for 'Download Prices' option...")
        download_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//p[contains(text(), 'Download Prices')]"))
        )
        download_button.click()
        print(f"[{datetime.now()}] Clicked 'Download Prices'")
        time.sleep(7)

        # Step 7: Wait for download to complete
        print(f"[{datetime.now()}] Waiting for CSV download to complete...")
        timeout = 60
        poll_interval = 2
        elapsed = 0
        csv_file_path = None

        while elapsed < timeout:
            csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
            if csv_files:
                csv_file_path = max(csv_files, key=os.path.getctime)
                print(f"[{datetime.now()}] CSV file downloaded: {csv_file_path}")
                break
            time.sleep(poll_interval)
            elapsed += poll_interval

        if not csv_file_path:
            print(f"[{datetime.now()}] No CSV file downloaded after {timeout} seconds!")
            raise Exception("CSV download failed")

        # Step 8: Read CSV content
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()

        print(f"[{datetime.now()}] Successfully read CSV data")
        return csv_content

    except Exception as e:
        print(f"[{datetime.now()}] Error fetching CSV: {str(e)}")
        try:
            driver.save_screenshot("/tmp/error_screenshot.png")
            print(f"[{datetime.now()}] Saved error screenshot to /tmp/error_screenshot.png")
            print(f"[{datetime.now()}] Current page source:")
            print(driver.page_source[:2000] + "... (truncated)")
        except Exception as screenshot_error:
            print(f"Screenshot capture failed: {screenshot_error}")
        return None

    finally:
        driver.quit()

def update_github_repo(csv_data):
    if not csv_data:
        print(f"[{datetime.now()}] No CSV data to commit")
        return

    print(f"[{datetime.now()}] Updating GitHub repository")

    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        github_repo = os.environ.get("GITHUB_REPOSITORY")

        print(f"[{datetime.now()}] Connecting to GitHub repository: {github_repo}")

        g = Github(github_token)
        repo = g.get_repo(github_repo)

        try:
            repo.get_contents("data")
            print(f"[{datetime.now()}] Data directory exists in repo")
        except:
            repo.create_file(
                "data/README.md",
                "Create data directory",
                "# CSV Data from PriceLabs\n\nThis directory contains automatically fetched CSV data."
            )
            print(f"[{datetime.now()}] Created data directory in repo")

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"data/pricelabs-{today}.csv"

        try:
            contents = repo.get_contents(filename)
            repo.update_file(
                path=filename,
                message=f"Update CSV data from PriceLabs - {today}",
                content=csv_data,
                sha=contents.sha
            )
            print(f"[{datetime.now()}] Updated file: {filename}")
        except:
            repo.create_file(
                path=filename,
                message=f"Add CSV data from PriceLabs - {today}",
                content=csv_data
            )
            print(f"[{datetime.now()}] Created file: {filename}")

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

if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting CSV fetch and GitHub update process")
    csv_data = fetch_csv_from_pricelabs()
    update_github_repo(csv_data)
    print(f"[{datetime.now()}] Process completed")
