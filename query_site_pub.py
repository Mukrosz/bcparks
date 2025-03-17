#!/usr/bin/python3
import argparse
import hashlib
import time
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from twilio.rest import Client
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

    print('SMS sent: {}'.format(message.sid))

def get_sites_availability(url):
    """
        Opens Chrome window with specific URL and checks for available sites.

        :param str url : camping.bcparks.ca URL to check
    """

    driver.get(url)

    try:
        # Wait for the main map container to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".map-container"))
        )
        #print("✅ .map-container element found!")

        attempts = 3  # Retry mechanism to handle stale elements
        available_sites = []

        for _ in range(attempts):
            try:
                # Locate the map container again in case it was refreshed
                map_container = driver.find_element(By.CSS_SELECTOR, ".map-container")

                # Wait for ALL map icons (ensures everything is loaded)
                WebDriverWait(map_container, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "map-icon"))
                )
                site_icons = map_container.find_elements(By.CLASS_NAME, "map-icon")

                for icon in site_icons:
                    try:
                        class_list = icon.get_attribute("class").split()

                        # Ensure only checking for available sites
                        if "icon-available" not in class_list:
                            continue  

                        # Try multiple ways to find the site label
                        site_label = "unknown"
                        try:
                            # Look for the label directly related to the icon
                            site_label_element = icon.find_element(By.XPATH, "./following-sibling::*[contains(@class, 'map-site-label')]")
                            site_label_text_element = site_label_element.find_element(By.CLASS_NAME, "resource-label")
                            site_label = site_label_text_element.text.strip()
                        except NoSuchElementException:
                            # Fallback: Try searching in a broader scope
                            try:
                                site_label_element = icon.find_element(By.XPATH, "../following-sibling::div[contains(@class, 'map-site-label')]")
                                site_label_text_element = site_label_element.find_element(By.CLASS_NAME, "resource-label")
                                site_label = site_label_text_element.text.strip()
                            except NoSuchElementException:
                                site_label = "unknown"

                        if site_label != "unknown" and site_label not in available_sites:
                            available_sites.append(site_label)

                    except StaleElementReferenceException:
                        print("🔄 Stale element detected, retrying...")
                        continue  # Try again

                break  # Exit loop if successful

            except StaleElementReferenceException:
                print("🔄 Stale element detected, retrying full loop...")
                continue  # Try again

        return sorted(available_sites)  # Ensure sorted list

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == '__main__':
    description = ("This scripts monitors for available sites based on the provided URL from the camping.bcparks.ca website \n"
                   "The script runs on a headless linux server\n"
                   "Tested on Debian 12.5(Bookworm) with latest Chrome \n"
                   "Example URL: \n"
                   "https://camping.bcparks.ca/create-booking/results?resourceLocationId=-2147483565&mapId=-2147483472&searchTabGroupId=0&bookingCategoryId=0&start%20%20%20%20Date=2024-08-05&endDate=2024-08-12&nights=7&isReserving=true&equipmentId=-32768&subEquipmentId=-32768&partySize=1&startDate=2024-08-05&filterData=%7B%7D \n\n" 
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
                   " echo 'deb [signed-by=/usr/share/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list\n"
                   "    sudo apt update\n"
                   "    sudo apt install google-chrome-stable\n\n"
                   "6. Install ChromeDriver \n"
                   "    CHROME_VERSION=$(google-chrome --version | awk '{print $3}')\n"
                   "    wget https://storage.googleapis.com/chrome-for-testing-public/$(CHROME_VERSION)/linux64/chromedriver-linux64.zip\n"
                   "    unzip chromedriver-linux64.zip\n"
                   "    mv chromedriver /usr/local/bin/\n"
                   "    chmod +x /usr/local/bin/chromedriver\n\n"
                   "5. Twilio (Optional)\n"
                   "    Create Twilio account and populate default twilio specific argparse args if sms is required \n\n"
                   " ---< Examples >--- \n"
                   "Check for site availability : \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...'  \n\n" 
                   "Check for site availability and get and sms notification: \n"
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
                         help     = 'URL from https://camping.bcparks.ca/create-booking',
                         required = True 
    )
    parser.add_argument('--interval', '--i',
                         help     = 'Interval between checks in seconds',
                         type     = int,
                         default  = 60,
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

    try:
        # Set up the Chrome driver
        options          = Options()
        options.add_argument('--headless')
        options.headless = True  # Run in headless mode for efficiency
        driver           = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        while True:
            available_sites = get_sites_availability(args.url)
            if available_sites:
                current_date = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                available_sites = ','.join(sorted(available_sites))
                print("{} - {}".format(current_date, available_sites))
                if args.sms:
                    send_sms(message     = '{} - {}: {}'.format(current_date, available_sites, args.url),
                             client      = client,
                             to_number   = args.my_phone_number,
                             from_number = args.twilio_number
                    )
            else:
                print("{} - No Availability".format(datetime.now().strftime("%Y-%m-%d_%H:%M:%S")))
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("Stopping the monitoring script.")
    except Exception as e:
        print("Error has occured: {}".format(e))
    finally:
        driver.quit()
