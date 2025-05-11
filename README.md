# CHAS Clinic Finder

A web application to search for CHAS (Community Health Assist Scheme) clinics near a specified Singapore postal code.

## Features

- Search for clinics within 3km of any Singapore postal code
- View detailed information about each clinic (name, address, phone, services)
- Filter clinics (all or dental only)
- Search within results by name, address, or service type
- Real-time progress tracking during searches

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install flask selenium webdriver-manager
```

3. Make sure you have Chrome browser installed (the application uses ChromeDriver)

## Running the Application

1. Start the application:

```bash
python app.py
```

2. Open your browser and go to `http://127.0.0.1:5000`
3. Enter a Singapore postal code (e.g., 654289) and click "Search for Clinics"
4. Wait for the search to complete, and view the results

## Deployment

This application can be deployed on any hosting platform that supports Python web applications. When deploying to production:

1. Set `debug=False` in the app.run() call for security
2. Ensure the server has Chrome or Chromium installed for Selenium
3. Consider setting up environment variables for any configuration you might need
4. Use a WSGI server like Gunicorn for production:
   ```bash
   pip install gunicorn
   gunicorn app:app
   ```
5. Consider using a reverse proxy like Nginx for improved performance and security

## How It Works

The application:
1. Uses Selenium to automate a browser that navigates to the CHAS clinic locator website
2. Inputs the postal code provided by the user
3. Searches for clinics within 3km of that location
4. Extracts clinic information from multiple pages of results
5. Displays the results in an interactive web interface

## Requirements

- Python 3.6+
- Flask
- Selenium
- Chrome browser

## Note

This application is for educational purposes only. Please respect the terms of service of the CHAS website when using this tool. 
