# Description
This script serves as a simple notification system for sites availability found on BC Parks Camping website.
Runs on a headless linux server.<br/><br/>
Example output:
```
2024-03-01 08:18:33 - No Availability
2024-03-01 08:19:23 - Available sites: 51, 58
SMS sent: SMaxxxxx
```

# Requirements
* linux OS (tested on Debian 12.5) 
* python3.11 (older may work, not tested)
* pip packages:
  * selenium
  * webdriver-manager
  * twilio (optional sms service)
* Chrome
* ChromeDriver (Chrome matching version)

# Install
## Python
> Create virtual envrionment
```
python3 -m venv bcparks
```

> Activate this virtual environment
```
. bcpark/bin/activate
```

> Install python dependencies
```
pip install selenium webdriver-manager
```

> Install Twilio module if you plan to receive SMS notifications (requires Twilio registration)
```
pip install twilio
```

## Google Chrome
> Add Google Chrome repo (Debian based)
```
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo tee /usr/share/keyrings/google-chrome.asc
echo 'deb [signed-by=/usr/share/keyrings/google-chrome.asc] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list
```
> Install Google Chrome
> 
```
sudo apt update
sudo apt install google-chrome-stable
```

## Google Chrome Driver
> This should install a matching version of Google Chrome Driver (important)
```
CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
cd /tmp/
wget https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
cd chromedriver-linux64/
mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver
```
# Usage
1. Navigate to [https://camping.bcparks.ca/create-booking/](url)
2. Select your Park, time frame and tent size, click Search
3. A map of available campsites should now be visible (Note: if there are multiple camp sites within the park, select the desired camp site)
4. Copy the URL (this is your `--u` argument)
> URL `--u` example:
```
https://camping.bcparks.ca/create-booking/results?resourceLocationId=-2147483504&mapId=-2147483312&searchTabGroupId=0&bookingCategoryId=0 \
&startDate=2025-08-18&endDate=2025-08-25&nights=7&isReserving=true&equipmentId=-32768&subEquipmentId=-32768 \
&searchTime=2025-04-01T10:25:15.774&flexibleSearch=%5Bfalse,false,%222025-04-01%22,1%5D&filterData=%7B%7D
```
<br/><br/>
> Activate bcpark virtual environment
```
. bcpark/bin/activate
```
<br/>

> Monitor availability of all spots in the campsite (green colored) every 60 seconds
```
./query_site_pub.py --u 'https://camping.bcparks.ca/create-booking...'
```
<br/>

> Monitor availability of specific spots in the campsite
```
./query_site_pub.py --u 'https://camping.bcparks.ca/create-booking...' --f '13,5,41,19`
```
<br/>

> Monitor availability of specific spots in the campsite every 20 seconds (default is 60 seconds)
```
./query_site_pub.py --u 'https://camping.bcparks.ca/create-booking...' --f '13,5,41,19` --i 20
```
<br/>

> Get notified by SMS when availability is detected:
> <br/>Note: this requires an active Twilio account
```
./query_site_pub.py --u 'https://camping.bcparks.ca/create-booking...' --s --i 30 --f '40,21' \
                    --twilio_sid X --twilio_auth_token X --twilio_number X \
                    --my_phone_number X
```

> Arguments
```
options:
  -h, --help            show this help message and exit
  --url URL             https://camping.bcparks.ca/create-booking...
  --interval INTERVAL, --i INTERVAL
                        Interval between checks in seconds
  --filter FILTER, --f FILTER
                        Filter specified sites
  --sms, --s            Enable SMS notification
  --twilio_sid TWILIO_SID, --tsid TWILIO_SID
                        Twilio account sid
  --twilio_auth_token TWILIO_AUTH_TOKEN, --tat TWILIO_AUTH_TOKEN
                        Twilio auth token
  --twilio_number TWILIO_NUMBER, --tn TWILIO_NUMBER
                        Twilio phone number
  --my_phone_number MY_PHONE_NUMBER, --mpn MY_PHONE_NUMBER
                        My phone number
```
