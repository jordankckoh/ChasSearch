from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
import threading
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

app = Flask(__name__)

# Store search results and status
search_results = {}
search_status = {"active": False, "total": 0, "completed": 0, "postal_code": "", "error": None}

def search_chas_clinics(postal_code):
    global search_results, search_status
    
    # Reset results and set status for new search
    search_results = {}
    search_status["active"] = True
    search_status["total"] = 0
    search_status["completed"] = 0
    search_status["postal_code"] = postal_code
    search_status["error"] = None
    
    # Initialize the webdriver with options
    options = webdriver.ChromeOptions()
    # Removing headless mode to show the browser window
    # options.add_argument("--headless")
    # options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    # Add user agent to appear more like a regular browser
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    all_clinics = []
    page = 0
    
    try:
        driver = webdriver.Chrome(options=options)
        
        # Open the CHAS clinic locator page
        driver.get("https://www.chas.sg/clinic-locator")
        
        # Check for and handle any cookie/consent dialogs
        try:
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow') or contains(text(), 'Agree') or contains(text(), 'Consent') or contains(text(), 'OK')]")
            if cookie_buttons:
                driver.execute_script("arguments[0].click();", cookie_buttons[0])
                time.sleep(1)
        except Exception:
            pass
        
        # Add initial waiting time for page to fully load
        time.sleep(2)
        
        try:
            # Wait for the distance dropdown to be available and click it
            dropdown_elements = driver.find_elements(By.CSS_SELECTOR, ".clinicDropdownLabel")
                
            # Now wait for the clickable element
            distance_dropdown = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".clinicDropdownLabel"))
            )
            # Use JavaScript to click in case of overlay issues
            driver.execute_script("arguments[0].click();", distance_dropdown)
            time.sleep(0.5)
            
            # Select "Within 3km" option
            within_3km_option = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'dropdown-item') and contains(text(), 'Within 3km')]"))
            )
            driver.execute_script("arguments[0].click();", within_3km_option)
            time.sleep(0.5)
     
            # Wait for the search input field to be available
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "clinicAddSearch"))
            )
            
            # Input the postal code
            search_term = f"{postal_code}"
            search_input.clear()
            search_input.send_keys(search_term)
            time.sleep(0.5)  # Wait for autocomplete suggestions
            search_input.send_keys(Keys.TAB)
            
            # Find and click the search button with the correct selector
            try:
                # Use CSS Selector with the exact class names
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.chas-button.search"))
                )
                
                # Try direct click first
                try:
                    search_button.click()
                except Exception as e:
                    print(f"Direct click failed: {str(e)}")
                    # If direct click fails, try JavaScript click
                    driver.execute_script("arguments[0].click();", search_button)
                
                # Give time for the click to take effect
                time.sleep(3)
                
            except Exception as e:
                print(f"Failed to find or click search button: {str(e)}")
                
                # Try alternative methods
                try:
                    # Try by XPath as fallback
                    search_button = driver.find_element(By.XPATH, "//button[contains(@class, 'chas-button') and contains(@class, 'search')]")
                    driver.execute_script("arguments[0].click();", search_button)
                    time.sleep(3)
                except Exception:
                    # Last resort: try Action Chains or submitting the form
                    try:
                        form = driver.find_element(By.TAG_NAME, "form")
                        form.submit()
                        time.sleep(3)
                    except Exception:
                        # As a final fallback, try using the Enter key
                        search_input = driver.find_element(By.ID, "clinicAddSearch")
                        search_input.send_keys(Keys.RETURN)
                        time.sleep(3)
            
            # Wait for search results to load
            finally:
                time.sleep(3)
            
            # Check if results loaded by looking for clinic cards
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card.clinicCard"))
                )
            except TimeoutException:
                pass
            
            # Process first 3 pages (or fewer if there aren't 3 pages)
            page = 1
            max_pages = 3
            
            while page <= max_pages:
                search_status["completed"] = page
                
                # Process current page
                page_clinics = process_page(driver)
                all_clinics.extend(page_clinics)
                
                # Try to find next page link
                try:
                    next_page_links = driver.find_elements(By.XPATH, f"//a[text()='{page+1}']")
                    if not next_page_links or page >= max_pages:
                        break
                        
                    # Click next page
                    driver.execute_script("arguments[0].click();", next_page_links[0])
                    time.sleep(1.5)  # Wait for next page to load
                    page += 1
                    
                except Exception:
                    break
            
            # Update search results
            search_results = {
                "postal_code": postal_code,
                "clinics": all_clinics,
                "total_clinics": len(all_clinics)
            }
            
            # Add a longer pause at the end to inspect the browser
            time.sleep(5)
            
        except TimeoutException as te:
            error_msg = f"Timeout while searching clinics: {str(te)}"
            search_status["error"] = error_msg
        
        except Exception as ex:
            error_msg = f"Error while searching clinics: {str(ex)}"
            search_status["error"] = error_msg
            
        finally:
            # Update status
            search_status["active"] = False
            search_status["total"] = page
                
    except Exception as e:
        error_msg = f"Failed to initialize browser or search: {str(e)}"
        search_status["active"] = False
        search_status["error"] = error_msg
        
    finally:
        # Close the browser
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def process_page(driver):
    # Collect all clinic cards
    clinic_cards = driver.find_elements(By.CSS_SELECTOR, ".card.clinicCard")
    page_clinics = []
    
    for card in clinic_cards:
        try:
            # Extract all clinic data regardless of type
            clinic_name = card.find_element(By.CSS_SELECTOR, ".clinicCardTitle").text.strip()
            clinic_address = card.find_element(By.CSS_SELECTOR, ".clinicAddress").text.strip()
            
            # Get clinic type
            try:
                clinic_type_elem = card.find_element(By.CSS_SELECTOR, ".clinicCardDetails:has(.fa-clinic-medical)")
                clinic_type_text = clinic_type_elem.text.strip()
            except Exception:
                clinic_type_text = "Not specified"
            
            # Extract phone number
            try:
                phone_elem = card.find_element(By.CSS_SELECTOR, ".clinicPhoneNum")
                phone_text = phone_elem.text.strip()
            except Exception:
                phone_text = "Not available"
            
            # Extract distance information
            try:
                distance_elem = card.find_element(By.CSS_SELECTOR, ".clinicCardDetails.distance")
                distance_text = distance_elem.text.strip()
                # Clean up the distance text
                if "km" in distance_text.lower():
                    distance_text = re.search(r'(\d+\.\d+km|\d+km)', distance_text.lower()).group(1)
            except Exception:
                distance_text = "NA"
            
            # Data structure for this clinic
            clinic_data = {
                "name": clinic_name,
                "address": clinic_address,
                "phone": phone_text,
                "type": clinic_type_text,
                "distance": distance_text,
                "is_dental": "dental" in clinic_type_text.lower()
            }
            
            page_clinics.append(clinic_data)
                
        except Exception:
            pass
    
    return page_clinics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    postal_code = request.form.get('postal_code', '')
    
    if not postal_code or not postal_code.isdigit() or len(postal_code) != 6:
        return render_template('index.html', error="Please enter a valid 6-digit Singapore postal code")
    
    # Start search in a separate thread to not block the web request
    search_thread = threading.Thread(target=search_chas_clinics, args=(postal_code,))
    search_thread.daemon = True
    search_thread.start()
    
    # Redirect to results page which will poll for status
    return redirect(url_for('results'))

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/api/status')
def get_status():
    return jsonify(search_status)

@app.route('/api/results')
def get_results():
    return jsonify(search_results)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Run the app
    app.run(debug=False) 