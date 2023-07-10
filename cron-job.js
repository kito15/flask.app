const cron = require('node-cron');
const axios = require('axios');

// Define the cron schedule (runs every hour)
const cronSchedule = '0 * * * *';

// Define the URL to be executed
const url = 'https://flask-production-d5a3.up.railway.app/authorize';

// Define the cron job
const job = cron.schedule(cronSchedule, async () => {
  try {
    // Send a GET request to the specified URL
    const response = await axios.get(url);

    // Log the response or perform any desired actions
    console.log(`GET request to ${url} was successful. Response:`, response.data);
  } catch (error) {
    console.error(`Error sending GET request to ${url}:`, error);
  }
});

// Start the cron job
job.start();
