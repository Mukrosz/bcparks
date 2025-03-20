#!/usr/bin/python3
import argparse
import time
from datetime import datetime

# Selenium
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# WebDriver Manager
from webdriver_manager.chrome import ChromeDriverManager

# Twilio API
from twilio.rest import Client

def comma_separated_list(value):
    """Converts a comma-separated string into a sorted list of numbers"""
    return sorted([item.strip() for item in value.split(',')], key = int)

def send_sms(message, client, to_number, from_number):
    """
    Send a text message to a phone number

    :param str message     : message to send as sms
    :param obj client      : Twilio obj instance
    :param str to_number   : the number to send the message to
    :param str from_number : Twilio number
    """

    message   = client.messages.create(
        to    = to_number,
        from_ = from_number,
        body  = message
    )

    print(f"SMS sent: {message.sid}")

def get_sites_availability(driver, url):
    """
    Retrieves available campsite listings, handling stale elements.

    :param obj driver: Selenium WebDriver instance
    :param str url: URL to check for campsite availability
    :return: Sorted list of available site names
    """
    try:
        driver.get(url)

        # Wait until the map-container is fully loaded
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".map-container"))
        )

        # Wait for all site icons to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "map-icon"))
        )

        max_retries = 3  # Number of retries for stale elements
        retry_delay = 1  # Initial delay for backoff

        for attempt in range(max_retries):
            try:
                # Re-fetch elements every retry
                site_icons = driver.find_elements(By.CLASS_NAME, "map-icon")
                available_sites = []

                for icon in site_icons:
                    try:
                        if "icon-available" in icon.get_attribute("class"):
                            # Locate the nearest label safely
                            site_label_element = icon.find_element(By.XPATH, "./following-sibling::*[contains(@class, 'map-site-label')]")
                            site_label_text_element = site_label_element.find_element(By.CLASS_NAME, "resource-label")
                            site_label = site_label_text_element.text.strip()

                            if site_label and site_label not in available_sites:
                                available_sites.append(site_label)

                    except StaleElementReferenceException:
                        print("🔄 Stale element detected, retrying...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        break  # Break out and retry fetching elements

                return sorted(available_sites, key = int)

            except StaleElementReferenceException:
                print(f"🔄 Retrying fetch attempt {attempt + 1}/{max_retries} due to stale elements...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Increase wait time on subsequent retries

        print("❌ Stale elements persisted after multiple attempts.")
        return []

    except TimeoutException:
        print("⚠ Timeout while loading page.")
        return []
    except WebDriverException as e:
        print(f"❌ WebDriver error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

def setup_webdriver():
    """
    Sets up and returns a Chrome WebDriver instance with optimized options.
    
    :return: WebDriver instance or None on failure
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')  # Helps stability in headless mode
    options.add_argument('--no-sandbox')   # Helps in some environments
    options.add_argument('--disable-dev-shm-usage')  # Helps with shared memory issues
    options.add_argument('--log-level=3')  # Suppress unnecessary logs

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(60)  # Prevent long waits on slow connections
        return driver
    except WebDriverException as e:
        print(f"❌ WebDriver failed to start: {e}")
        return None

if __name__ == '__main__':
    description = ("This scripts monitors for available sites based on the provided URL from the camping.bcparks.ca website \n"
                   "The script runs on a headless linux server\n"
                   "Tested on Debian 12.5(Bookworm) with latest Chrome \n"
                   "Example URL: \n"
                   "https://camping.bcparks.ca/create-booking/results?mapId=-2147483376&searchTabGroupId=0&bookingCategoryId=0&startDate=2025-07-07&endDate=2025-07-14&nights=7&isReserving=true&equipmentId=-32768&subEquipmentId=-32768&filterData=%7B%7D"
                   "---< Setup >--- \n"
                   "1. Ensure you are running python3.11 \n"
                   "2. Create virtual env: \n"
                   "    python3 -m venv bcparks \n"
                   "3. Activate this env: \n"
                   "    . bcpark/bin/activate \n"
                   "4. Install dependencies \n"
                   "    pip install twilio selenium webdriver-manager\n"
                   "5. Install Chrome \n"
                   "    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo tee /usr/share/keyrings/google-chrome.asc\n"
                   "    echo 'deb [signed-by=/usr/share/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list\n"
                   "    sudo apt update\n"
                   "    sudo apt install google-chrome-stable\n\n"
                   "6. Install ChromeDriver \n"
                   "    CHROME_VERSION=$(google-chrome --version | awk '{print $3}')\n"
                   "    wget https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip\n"
                   "    unzip chromedriver-linux64.zip\n"
                   "    mv chromedriver /usr/local/bin/\n"
                   "    chmod +x /usr/local/bin/chromedriver\n\n"
                   "5. Twilio (Optional)\n"
                   "    Create Twilio account and populate default twilio specific argparse args if sms is required \n\n"
                   " ---< Examples >--- \n"
                   "Check for site availability : \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...'  \n\n" 
                   "Check for site availability for specific sites : \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --f '10,92'  \n\n" 
                   "Check for site availability and get and sms notification (check twilio_* arguments): \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --s \n\n"
                   "Check for site availability every 30s insead the default 60s: \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --s --i 30 \n\n"
                   "Override sms Twilio args: \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --s --i 30 \\\n"
                   "                  --twilio_sid X --twilio_auth_token X --twilio_number X \\\n"
                   "                  --my_phone_number X \n\n")
    parser = argparse.ArgumentParser(description     = description,
                                     formatter_class = argparse.RawTextHelpFormatter
    )
    parser.add_argument('--url',
                         help     = 'Example URL https://camping.bcparks.ca/create-booking/results?mapId=-2147483376&searchTabGroupId=0&bookingCategoryId=0&startDate=2025-07-07&endDate=2025-07-14&nights=7&isReserving=true&equipmentId=-32768&subEquipmentId=-32768&filterData=%7B%7D',
                         required = True 
    )
    parser.add_argument('--interval', '--i',
                         help     = 'Interval between checks in seconds',
                         type     = int,
                         default  = 60,
                         required = False
    )
    parser.add_argument('--filter','--f',
                         help     = 'Filter specified sites',
                         type     = comma_separated_list,
                         required = False 
    )
    parser.add_argument('--sms', '--s',
                         help     = 'Enable SMS notification',
                         action   = 'store_true',
                         default  = False,
                         required = False
    )
    parser.add_argument('--twilio_sid', '--tsid',
                         help     = 'Twilio account sid',
                         default  = '',
                         required = False
    )
    parser.add_argument('--twilio_auth_token', '--tat',
                         help     = 'Twilio auth token',
                         default  = '',
                         required = False
    )
    parser.add_argument('--twilio_number', '--tn',
                         help     = 'Twilio phone number',
                         default  = '',
                         required = False
    )
    parser.add_argument('--my_phone_number', '--mpn',
                         help     = 'My phone number',
                         default  = '',
                         required = False
    )

    args = parser.parse_args()

    if args.sms:
        # Initialize Twilio client
        client = Client(args.twilio_sid, args.twilio_auth_token)

    driver = setup_webdriver()
    if not driver:
        print("❌ WebDriver initialization failed. Exiting...")
        exit(1)

    try:
        while True:
            available_sites = get_sites_availability(driver, args.url)

            if args.filter:
                available_sites = [site for site in args.filter if site in available_sites]

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if available_sites:
                print(f"{timestamp} - Available sites: {', '.join(available_sites)}")
                if args.sms:
                    send_sms(f"{timestamp} - Available sites: {', '.join(available_sites)}\n{args.url}",
                             client, args.my_phone_number, args.twilio_number)
            else:
                print(f"{timestamp} - No Availability")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("Stopping the script.")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    finally:
        driver.quit()
