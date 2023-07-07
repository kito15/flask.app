import requests
import schedule
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def run_job():
    url = "https://flask-production-d5a3.up.railway.app/authorize"
    response = requests.get(url)
    if response.status_code == 200:
        logging.info("Job executed successfully")
    else:
        logging.error(f"Job failed with status code: {response.status_code}")

# Schedule the job to run every hour
schedule.every().hour.do(run_job)

# Run the scheduler indefinitely
while True:
    schedule.run_pending()
    time.sleep(1)
