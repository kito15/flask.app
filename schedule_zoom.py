import requests
import schedule
import time
from flask import Flask

app = Flask(__name__)

def run_job():
    url = "https://flask-production-d5a3.up.railway.app/authorize"
    response = requests.get(url)
    if response.status_code == 200:
        logging.info("Job executed successfully")
    else:
        logging.error(f"Job failed with status code: {response.status_code}")

# Schedule the job to run every hour
schedule.every().hour.do(run_job)

@app.route('/trigger', methods=['POST'])
def trigger_job():
    run_job()
    return 'Job triggered'

while True:
    schedule.run_pending()
    time.sleep(1)
