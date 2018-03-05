from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from influxdb import InfluxDBClient
import time
import os, subprocess
import re
from datetime import datetime

JOB_KEYWORDS = ["ruby", "ruby on rails", "angular", "node", "react", "javascript", "react native", "automation", "test", "java", "c#", "visual studio", ".net"]
CITIES_INDIANAPOLIS = ["Indianapolis, Indiana", "Fishers, Indiana", "Carmel, Indiana"]
CITIES = ["Indianapolis, Indiana", "Louisville, Kentucky", "Chicago, Illinois", "Columbus, Ohio", "Cincinnati, Ohio", "Cleveland, Ohio", "Saint Louis, Missouri", "Detroit, Michigan", "Milwaukee, Wisconsin", "Madison, Wisconsin"]
URLS = ["https://www.linkedin.com/jobs"]

driver = None
client = None

# on Linux, the command is "netsh wlan show interfaces"
# on Mac, the command is "airport -s", but first you have to enter "sudo ln -s /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport /usr/local/bin/airport"
if str.encode(os.environ['HOME_WIFI_SSID']) in subprocess.check_output("airport -s", shell=True):
    print("connecting to LAN file server")
    client = InfluxDBClient(os.environ['HOME_IP_ADDRESS'], 8086, 'root', 'root', 'jobs')
else:
    print("connecting remotely to file server")
    client = InfluxDBClient(os.environ['REMOTE_IP_ADDRESS'], 8086, 'root', 'root', 'jobs')
print(client)
client.create_database('jobs')

try:
    for url in URLS:
        driver = webdriver.Firefox()
        driver.get("https://www.linkedin.com/jobs/")

        # login
        login = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Sign in")))
        login.click()
        email_address = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "session_key-login")))
        email_address.clear()
        email_address.send_keys(os.environ['LINKEDIN_USERNAME'])
        time.sleep(1)
        password = driver.find_element(By.ID, "session_password-login")
        password.clear()
        password.send_keys(os.environ['LINKEDIN_PASSWORD'])
        time.sleep(1)
        password.send_keys(Keys.RETURN)
        for keyword in JOB_KEYWORDS:
            for city in CITIES:
                # search for jobs
                title = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search jobs']")))
                title.clear()
                title.send_keys(keyword)
                location = driver.find_element(By.XPATH, "//input[@placeholder='Search location']")
                location.clear()
                location.send_keys(city)
                time.sleep(2)
                location.send_keys(Keys.RETURN)
                time.sleep(5)
                num_jobs = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "results-count-string")))
                #int_num_jobs = driver.find_elements(By.CLASS_NAME, "results-count-string")[0].get_attribute("innerHTML").strip()
                int_num_jobs = int(re.search(r'\d+', driver.find_elements(By.CLASS_NAME, "results-count-string")[0].get_attribute("innerHTML").strip()).group())
                json_body = [
                    {
                        "measurement": "num_jobs",
                        "time": datetime.now(),
                        "fields": {
                            "keyword": keyword,
                            "city": city,
                            "number_of_jobs": int_num_jobs
                        }
                    }
                ]
                print(json_body)
                client.write_points(json_body)
                time.sleep(5)
        driver.quit()
except Exception as e:
    if driver != None:
        driver.quit()
        print(e)
        print("driver is shut down")