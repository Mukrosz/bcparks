#!/usr/bin/env python3

import argparse
import re
import sys
import time
from datetime import datetime

def shorten_url(url):
    """Convert long URLs to short """
    s = pyshorteners.Shortener()
    return s.tinyurl.short(url)

def current_time():
    """Return current date in a desired format"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def pp(message, error = False):
    """
    Regular print but prefixed with current timestamp

    :param str message : title of the message 
    """
    if error:
        sys.exit('{} - {}'.format(current_time(), message))
    else:
        print('{} - {}'.format(current_time(), message))

def comma_separated_list(value):
    """Converts a comma-separated string into a list"""
    return [item.strip().lower() for item in value.split(',')]

def sort_key(s):
    """
    Natural sorting function used by sorted that
    sorts a list of alphanumeric values (excluding special characters)

    :param s : alphanumeric value (examples: 2, S15, 18B) 
    :return  : a tuple (example: ("", 2, "") or ("S", 15, "") or ("", 18, "B")
    """
    match = re.match(r'([A-Za-z]*)(\d+)([A-Za-z]*)', s.strip())
    if match:
        prefix, number, suffix = match.groups()
        return (prefix, int(number), suffix)
    return (s, 0, '')  # fallback if unmatched

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

    pp('SMS sent: {}'.format(message.sid))

def get_available_sites(driver, url, max_attempts = 5, retry_delay = 1):
    """
    Returns a dictionary of {label: icon_element} for all available campsites,
    with retries and smarter load timing to avoid stale references.
    """

    for attempt in range(max_attempts):
        available = []

        try:
            pp('⏳ Scanning for available sites (attempt {}/{})...'.format(attempt + 1, max_attempts))
            driver.get(url)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.map-container'))
            )

            WebDriverWait(driver, 15).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, 'map-icon')) > 10
            )

            # Optional: wait for icon count to stabilize
            stable_count = 0
            last_count = 0
            for _ in range(5):
                icons = driver.find_elements(By.CLASS_NAME, 'map-icon')
                count = len(icons)
                if count == last_count:
                    stable_count += 1
                    if stable_count >= 2:
                        break
                else:
                    stable_count = 0
                    last_count = count
                time.sleep(0.5)

            icons = driver.find_elements(By.CLASS_NAME, 'map-icon')

            for i, icon in enumerate(icons):
                try:
                    if 'icon-available' not in icon.get_attribute('class'):
                        continue

                    label_el = icon.find_element(By.XPATH, './following-sibling::*[contains(@class, "map-site-label")]')
                    label_text = label_el.find_element(By.CLASS_NAME, 'resource-label').text.strip().lower()

                    if label_text:
                        available.append(label_text)

                except (StaleElementReferenceException, NoSuchElementException) as e:
                    pp('⚠️  Skipped icon[{}] due to: {}'.format(i, type(e).__name__))
                    continue

            return available

        except TimeoutException:
            pp('❌ Timeout waiting for icons or map')
        except WebDriverException as e:
            pp('❌ WebDriver error: {}'.format(e))
            break
        except Exception as e:
            pp('❌ Unexpected error: {}'.format(e))

        time.sleep(retry_delay)

    pp('❌ Failed to retrieve available sites after {} attempts'.format(max_attempts))
    return {}

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
        pp('❌ WebDriver failed to start: {}'.format(e))
        return None

if __name__ == '__main__':
    try:
        from selenium import webdriver
        from selenium.common.exceptions import (
            StaleElementReferenceException,
            TimeoutException,
            WebDriverException,
            NoSuchElementException
        )
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        sys.exit('Error: selenium or webdriver_manager module not found. Install with `pip install selenium webdriver-manager`')

    description = ("This script monitors available campsites based on the provided URL \n"
                   "For full README, check https://github.com/Mukrosz/parks \n"
                   " ---< Examples >--- \n"
                   "Check for site availability : \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...'  \n\n" 
                   "Check for site availability for specific sites : \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --f '10,92,S18,S32B'  \n\n" 
                   "Check for site availability and get and sms notification (check twilio_* arguments): \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --s \n\n"
                   "Check for site availability every 30s insead the default 60s: \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --s --i 30 \n\n"
                   "Get an SMS notification when a site becomes available (requires Twilio account): \n"
                   "  ./query_site.py --u 'https://camping.bcparks.ca/create-booking...' --s --i 30 \\\n"
                   "                  --twilio_sid X --twilio_auth_token X --twilio_number X \\\n"
                   "                  --my_phone_number X \n\n")
    parser = argparse.ArgumentParser(description     = description,
                                     formatter_class = argparse.RawTextHelpFormatter
    )
    parser.add_argument('--url',
                         help     = 'https://camping.bcparks.ca/create-booking...',
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
        try:
            from twilio.rest import Client
            client = Client(args.twilio_sid, args.twilio_auth_token)
        except ImportError:
            sys.exit('Error: Twilio module not found. Install with `pip install twilio`')

        try:
            import pyshorteners
        except ImportError:
            sys.exit('Error: pyshorteners module not found. Please install it using `pip install pyshorteners`')

    driver = setup_webdriver()
    if not driver:
        sys.exit('❌ WebDriver initialization failed. Exiting...')

    try:
        while True:
            available_sites = get_available_sites(driver, args.url)

            if args.filter:
                available_sites = [site for site in args.filter if site in available_sites]

            if available_sites:
                pp('✨ Found {} available sites: {}'.format(len(available_sites),','.join(sorted(available_sites, key=sort_key))))
                if args.sms:
                    send_sms('{} - Available sites: {}\n{}'.format(current_time(),','.join(available_sites), shorten_url(args.url)),
                              client,args.my_phone_number, args.twilio_number
                    )
            else:
                pp('❌ No Availability')

            time.sleep(args.interval)

    except KeyboardInterrupt:
        pp('🛑 Script interrupted by user')
    except Exception as e:
        pp('❌ Unexpected error: {}'.format(e))
    finally:
        driver.quit()
