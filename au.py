import pyautogui
import time as t
import os 
import pyperclip
import spacy
from bs4 import BeautifulSoup
import requests
#import opencv_python as cv2
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

CONFIG = {
    'BROWSER_LOAD_TIME': 10,
    'TAB_LOAD_TIME': 5,
    'INPUT_DELAY': 1,
    'URL_LOAD_TIME': 15,
    'SEARCH_BAR_WAIT_TIME':    3,  # Added constant for search bar wait time
    'SEARCH_QUERY_WAIT_TIME': 5,  # Added constant for search query wait time
    'FIREFOX_PATH': r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    'SEARCH_TERMS': ["scrap", "search", "find", "read", "watch", "learn", "explore", "discover"],
    'PREPOSITIONS': ["on", "at", "in"]
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_sm")

def validate_input(user_input):
    """
    Validates user input
    
    Args:
        user_input (str): User input to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(user_input, str):
        logger.error("Input must be a string")
        return False
    
    if not user_input or len(user_input.strip()) == 0:
        logger.error("Input cannot be empty")
        return False
        
    if len(user_input) > 500:  # Add reasonable limit
        logger.error("Input too long")
        return False
        
    return True

user_input = pyautogui.prompt(text="enter your query", title="Autoscrap")
if not validate_input(user_input):
    logger.error("Invalid input provided")
    exit(1)


#NLP pipeline
def extract_info(user_input):
    doc = nlp(user_input)
    website = None
    purpose = None
    for ent in doc.ents:
        if ent.label_ == "ORG" or ent.label_ == "WEBSITE":
            website = ent.text.lower()
    if website is None:
        # Try to extract the website from the text
        for token in doc:
            if token.text.lower() in CONFIG['PREPOSITIONS']:
                website = token.nbor().text.lower()

    for token in doc:
        if token.text.lower() in CONFIG['SEARCH_TERMS']:
            purpose = ""
            for next_token in doc[token.i+1:]:
                purpose += next_token.text + " "
            purpose = purpose.strip()
    return website, purpose

website, purpose = extract_info(user_input)
logger.info(f"Website: {website}")
logger.info(f"Purpose: {purpose}")



def generate_url(website):
    if not website:
        return None
    if "http" in website:
        return website.lower()
    elif "." in website:
        return "https://" + website.lower()
    else:
        return "https://" + website + ".com"


def find_search_bar(driver):
    """
    Finds the search bar element using Selenium after PyAutoGUI loads the page.
    
    Args:
        driver (webdriver): The Selenium WebDriver instance.
        
    Returns:
        search_bar (WebElement or None): The search bar element if found, None otherwise.
    """
    try:
        wait = WebDriverWait(driver, CONFIG['SEARCH_BAR_WAIT_TIME'])
        
        # Website-specific selectors
        SEARCH_SELECTORS = {
            'medium.com': [
                ".js-searchInput",
                "[data-testid='search-input']",
                "input[placeholder*='Search Medium']"
            ],
            'twitter.com': [
                "[data-testid='SearchBox_Search_Input']",
                "[aria-label='Search query']",
                "input[placeholder*='Search']"
            ],
            'x.com': [  # Add X.com specific selectors
                "[data-testid='SearchBox_Search_Input']",
                "[aria-label='Search query']"
            ],
            'wikipedia.org': [
                "#searchInput",
                "#searchform input"
            ],
            'quora.com': [
                ".q-input input",
                "[placeholder*='question' i]"
            ],
            'generic': [
                "input[type='search']",
                "input[name*='search']",
                "input[placeholder*='search' i]",
                "input[aria-label*='search' i]",
                ".search-input",
                "#search"
            ]
        }

        # Determine which selectors to try first based on URL
        current_url = driver.current_url.lower()
        site_specific_selectors = []
        
        for domain, selectors in SEARCH_SELECTORS.items():
            if domain in current_url and domain != 'generic':
                site_specific_selectors = selectors
                break
                
        # Try site-specific selectors first, then generic ones
        all_selectors = site_specific_selectors + SEARCH_SELECTORS['generic']
        
        for selector in all_selectors:
            try:
                search_bar = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if search_bar.is_displayed() and search_bar.is_enabled():
                    logger.info(f"Found search bar using selector: {selector}")
                    return search_bar
            except (TimeoutException, NoSuchElementException):
                continue
                
        logger.error("No search bar found")
        return None
        
    except Exception as e:
        logger.error(f"Error in find_search_bar: {e}")
        return None


def check_browser_installed():
    if not os.path.exists(CONFIG['FIREFOX_PATH']):
        logger.error("Firefox is not installed")
        return False
    return True


def automate_search(url, purpose):
    """
    Automates the process of searching on a website using Firefox browser with pyautogui and Selenium.
    
    Args:
        url (str): The URL to navigate to
        purpose (str): The search query to type in the search bar
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not check_browser_installed():
            return False
            
        # Create Selenium driver to launch Firefox with a specific profile
        profile_path = r"C:\Users\Umarzaib\AppData\Roaming\Mozilla\Firefox\Profiles\no2mg4nx.default-release-1-1739563850354"
        options = FirefoxOptions()
        options.binary_location = CONFIG['FIREFOX_PATH']
        options.add_argument(f'--profile {profile_path}')
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        
        # Use Selenium to navigate to URL
        driver.get(url)
        t.sleep(CONFIG['URL_LOAD_TIME'])
        
        # Use Selenium to find and interact with search bar
        try:
            search_bar = find_search_bar(driver)
            if search_bar:
                search_bar.click()
                search_bar.clear()
                search_bar.send_keys(purpose)
                t.sleep(CONFIG['INPUT_DELAY'])  # Ensure the input is fully typed
                pyautogui.hotkey("enter")  # Simulate pressing Enter
                pyautogui.doubleClick()  # Simulate double-click to ensure search is triggered
                logger.info("Search query submitted successfully")
                t.sleep(CONFIG['SEARCH_QUERY_WAIT_TIME'] + 5)  # Wait additional 5 seconds
                return True
            else:
                logger.error("Could not find search bar")
                return False
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"An error occurred during automation: {e}")
        return False


if website is not None:
    url = generate_url(website)
    print("Generated URL:", url)
    automate_search(url, purpose)

else:
    print("Unable to extract website from input.")




