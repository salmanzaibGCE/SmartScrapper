# Standard library imports
import os
import time as t
import logging
import json
import csv
import cv2
import re
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin, parse_qs

# Third-party imports
import pyautogui
import pyperclip
import spacy
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.remote_connection import FirefoxRemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.firefox import GeckoDriverManager
import psutil

CONFIG = {
    'BROWSER_LOAD_TIME': 10,
    'TAB_LOAD_TIME': 5,
    'INPUT_DELAY': 1,
    'URL_LOAD_TIME': 15,
    'SEARCH_BAR_WAIT_TIME': 3,  # Added constant for search bar wait time
    'SEARCH_QUERY_WAIT_TIME': 5,  # Added constant for search query wait time
    'FIREFOX_PATH': r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    'SEARCH_TERMS': ["scrap", "search", "find", "read", "watch", "learn", "explore", "discover"],
    'PREPOSITIONS': ["on", "at", "in"],
    'MAX_POSTS': 5,  # Maximum number of posts to scrape
    'SCROLL_PAUSE_TIME': 2,  # Time to pause between scrolls
    'POST_LOAD_TIME': 3,  # Time to wait for post to load
    'OUTPUT_DIR': 'scraped_content',
    'MEDIA_DIR': 'media',
    'SUPPORTED_SITES': {
        'medium.com': {
            'title': ['h1', 'h1.pw-post-title', '[data-testid="storyTitle"]'],
            'author': ['[data-testid="authorName"]', '[rel="author"]', '.pw-author'],
            'date_posted': ['time', '[datetime]'],
            'read_time': ['.pw-reading-time', '[data-testid="storyReadTime"]'],
            'claps_likes': ['.pw-multi-vote-count', '[data-testid="clapsCount"]'],
            'main_content': ['article', '.story-content', '[data-testid="storyContent"]'],
            'topics_tags': ['.pw-tags-list', '[data-testid="topicsList"]'],
            'media': ['img.progressiveMedia-image', 'img.graf-image'],
            'embedded_links': ['a[href*="medium.com"]', '.graf-anchor'],
            'code_snippets': ['pre', 'code', '.graf-code']
        },
        'x.com': {  # Updated Twitter/X.com selectors
            'tweet': ['[data-testid="tweetText"]', '.tweet-text'],
            'author': ['[data-testid="User-Name"]', '.fullname'],
            'username': ['[data-testid="User-Username"]', '.username'],
            'date_posted': ['time', '[datetime]'],
            'media': ['[data-testid="tweetPhoto"]', '[data-testid="tweetVideo"]'],
            'likes': ['[data-testid="like"]', '.ProfileTweet-action--favorite'],
            'retweets': ['[data-testid="retweet"]', '.ProfileTweet-action--retweet'],
            'replies': ['[data-testid="reply"]', '.ProfileTweet-action--reply'],
            'quoted_tweet': ['[data-testid="quotedTweet"]'],
            'links': ['a[href]:not([href*="x.com"]):not([href*="twitter.com"])']
        }
    },
    
    'SEARCH_SELECTORS': {
        'medium.com': [
            ".js-searchInput",
            "[data-testid='search-input']",
            "input[placeholder*='Search Medium']"
        ],
        'x.com': [
            "[data-testid='SearchBox_Search_Input']",
            "[aria-label='Search query']",
            "input[placeholder*='Search']"
        ]
    },
    
    'POST_SELECTORS': {
        'medium.com': [
            "article h2 a",  # Most common Medium story link pattern
            "article h3 a",  # Alternative story link pattern
            "a[href*='/p/']",  # Medium post URLs containing /p/
            "a.ae.af",  # Medium's story card links
            ".postArticle-content a",  # Another common pattern
            "div[data-testid='postPreview'] a",  # Latest Medium selector
            "a[data-testid='storyCard']"  # Story card links
        ],
        'x.com': [
            "[data-testid='tweet']",
            "[data-testid='tweetText']",
            ".tweet",
            "[role='article']"
        ]
    },
    
    'CSV_COLUMNS': [
        'timestamp', 'site_type', 'url', 'title', 'author', 'username',
        'date_posted', 'read_time', 'claps_likes', 'retweets', 'replies',
        'main_content', 'topics_tags', 'media_urls', 'embedded_links',
        'quoted_content', 'code_snippets'
    ],
    'FIREFOX_PROCESS_NAMES': ['firefox.exe', 'firefox'],
    'REMOTE_DEBUGGING_PORT': 9222,
    'EXISTING_WINDOW_TIMEOUT': 5,
    'FIREFOX_PROFILE_PATH': os.path.expanduser('~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles'),
    'SPECIFIC_PROFILE': 'no2mg4nx.default-release-1-1739563850354',
    'USE_DEFAULT_PROFILE': True,
    'OPERATION_DELAY': 3,  # Delay between major operations
    'SCRAPING_COOLDOWN': 5,  # Cooldown after scraping
    'USER_INPUT_DELAY': 2,  # Delay after user input
    'FINAL_DISPLAY_DELAY': 3  # Delay before showing results
}

CONFIG.update({
    'CURRENT_SESSION_ID': datetime.now().strftime('%Y%m%d_%H%M%S'),  # Unique session identifier
    'SHOW_ONLY_CURRENT_SESSION': True  # Flag to control results display
})

CONFIG.update({
    'SEARCH_RESULTS_SELECTORS': {
        'medium.com': [
            'article',
            '.postArticle',
            '[data-post-id]',
            '.streamItem',
            '.js-postElement'
        ],
        'x.com': [
            '[data-testid="tweet"]',
            '.tweet',
            '[role="article"]'
        ],
        'generic': [
            'article',
            '.post',
            '.entry',
            '.item'
        ]
    }
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_sm")

def validate_input(user_input):
    """
    Validate user input for safety and constraints.
    
    Args:
        user_input (str): The input string to validate
        
    Returns:
        bool: True if input is valid, False otherwise
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

#NLP pipeline
def extract_info(user_input):
    """
    Extract website and purpose from user input using NLP.
    
    Args:
        user_input (str): User's search query text
        
    Returns:
        tuple: Contains:
            - website (str): Extracted website name or None
            - purpose (str): Extracted search purpose or None
    """
    doc = nlp(user_input)
    website = None
    purpose = None
    
    # Extract website from named entities
    for ent in doc.ents:
        if ent.label_ in ("ORG", "WEBSITE"):
            website = ent.text.lower()
            break
    
    # Fallback: Try to extract website from prepositions
    if website is None:
        for token in doc:
            if token.text.lower() in CONFIG['PREPOSITIONS']:
                website = token.nbor().text.lower()
                break

    # Extract purpose from search terms
    for token in doc:
        if token.text.lower() in CONFIG['SEARCH_TERMS']:
            purpose = " ".join(t.text for t in doc[token.i+1:])
            purpose = purpose.strip()
            break
            
    return website, purpose

def generate_url(website):
    """
    Generate a valid URL from website name.
    
    Args:
        website (str): Website name or domain
        
    Returns:
        str or None: Full URL with https:// prefix or None if invalid
    """
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
    """
    Check if Firefox browser is installed in the specified path.
    
    Returns:
        bool: True if Firefox is found, False otherwise
    """
    if not os.path.exists(CONFIG['FIREFOX_PATH']):
        logger.error("Firefox is not installed")
        return False
    return True

def open_first_post_with_pyautogui(driver):
    """Locate and click the first story post using PyAutoGUI image recognition."""
    try:
        t.sleep(CONFIG['POST_LOAD_TIME'] * 2)  # Add extra delay before PyAutoGUI
        # Try to find the first post with different confidence levels
        confidence_levels = [0.8, 0.7, 0.6]
        for confidence in confidence_levels:
            first_post = pyautogui.locateOnScreen("first_post.png", confidence=confidence, grayscale=True)
            if first_post:
                post_center = pyautogui.center(first_post)
                pyautogui.moveTo(post_center.x, post_center.y, duration=0.5)
                pyautogui.doubleClick()
                logger.info(f"Successfully clicked first post with post center {post_center} confidence {confidence}")
                t.sleep(CONFIG['TAB_LOAD_TIME'])
                return True
                
        logger.error("Could not locate first post image")
        return False
        
    except Exception as e:
        logger.error(f"Error in PyAutoGUI post opening: {e}")
        return False


def automate_search_with_pyautogui(url, purpose):
    """
    Automate the search process on Medium using Selenium for navigation and PyAutoGUI to open the first post.
    This function is consistent with your other automation functions.
    """
    try:
        if not check_browser_installed():
            return False
            
        driver = setup_firefox_driver()
        if not driver:
            return False
            
        try:
            # Navigate to the generated URL
            driver.get(url)
            t.sleep(CONFIG['URL_LOAD_TIME'])
            
            # Find and interact with the search bar (DOM-based)
            search_bar = find_search_bar(driver)
            if search_bar:
                logger.info("Starting search process...")
                t.sleep(CONFIG['OPERATION_DELAY'])
                search_bar.clear()
                search_bar.send_keys(purpose)
                t.sleep(CONFIG['INPUT_DELAY'])
                search_bar.send_keys(Keys.RETURN)
                t.sleep(CONFIG['SEARCH_QUERY_WAIT_TIME'])
            else:
                logger.error("Search bar not found")
                return False
            
            # Use PyAutoGUI to locate and open the first post
            if open_first_post_with_pyautogui(driver):
                # Switch Selenium to the new tab opened by PyAutoGUI's double-click
                driver.switch_to.window(driver.window_handles[-1])
                logger.info("Switched to new tab opened by PyAutoGUI")
                
                # Proceed with your current scraping strategy on the new tab
                if scrape_blog_content(driver):
                    logger.info("Scraping on the first post succeeded.")
                else:
                    logger.error("Scraping on the first post failed.")
            else:
                logger.error("Failed to open the first post using PyAutoGUI.")
                return False

            # Additional processing steps can be added here if needed.
            return True
            
        finally:
            if driver:
                t.sleep(CONFIG['OPERATION_DELAY'])
                driver.quit()
    except Exception as e:
        logger.error(f"Error during automation with PyAutoGUI: {e}")
        return False

           
    
          

def setup_directories():
    """
    Create necessary directories for storing scraped content.
    
    Returns:
        Path: Path object pointing to the output directory
    """
    Path(CONFIG['OUTPUT_DIR']).mkdir(exist_ok=True)  # Creates 'scraped_content' directory
    Path(CONFIG['MEDIA_DIR']).mkdir(exist_ok=True)   # Creates 'media' directory
    return Path(CONFIG['OUTPUT_DIR'])

def clean_filename(url):
    """
    Clean URL to create valid filename while preserving extension.
    
    Args:
        url (str): URL of the media file
        
    Returns:
        str: Cleaned filename safe for filesystem use
    """
    try:
        # Extract filename from URL and remove invalid characters
        parsed = urlparse(url)
        base_name = os.path.basename(parsed.path)
        
        # Replace invalid characters with underscore
        cleaned_name = re.sub(r'[\\/*?:"<>|]', '_', base_name)
        cleaned_name = re.sub(r'[^\w\-_.]', '_', cleaned_name)
        
        # If no extension or invalid filename, generate hash-based name
        if not cleaned_name or '.' not in cleaned_name:
            ext = '.jpg'  # Default extension
            hash_name = hashlib.md5(url.encode()).hexdigest()
            cleaned_name = f"{hash_name}{ext}"
            
        return cleaned_name
    except Exception as e:
        logger.error(f"Error cleaning filename for {url}: {e}")
        return hashlib.md5(url.encode()).hexdigest() + '.jpg'

def download_media(url, media_type):
    """
    Download media files with proper URL handling.
    
    Args:
        url (str): URL of the media to download
        media_type (str): Type of media (e.g., 'image', 'video')
        
    Returns:
        str or None: Path to saved file or None if download failed
    """
    try:
        # Clean and validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https:' + url if url.startswith('//') else 'https://' + url
                
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            filename = clean_filename(url)
            filepath = Path(CONFIG['MEDIA_DIR']) / f"{media_type}_{filename}"
            
            # Ensure media directory exists
            Path(CONFIG['MEDIA_DIR']).mkdir(exist_ok=True)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return str(filepath)
    except Exception as e:
        logger.error(f"Failed to download media from {url}: {e}")
    return None

def get_site_specific_scraper(url):
    """
    Determine appropriate scraper based on URL domain.
    
    Args:
        url (str): Website URL to analyze
        
    Returns:
        str: Site type identifier ('medium.com', 'x.com', or 'generic')
    """
    domain = urlparse(url).netloc
    if 'medium.com' in domain:
        return 'medium.com'
    elif any(x in domain for x in ['x.com', 'twitter.com']):
        return 'x.com'
    return 'generic'

def setup_csv_file():
    """Initialize CSV file with proper headers."""
    try:
        csv_path = Path(CONFIG['OUTPUT_DIR']) / 'scraped_data.csv'
        
        headers = CONFIG['CSV_COLUMNS']
        
        # Create new file with headers
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
        logger.info(f"Created new CSV file with {len(headers)} columns")
        return csv_path
    except Exception as e:
        logger.error(f"Failed to setup CSV file: {e}")
        return None

def extract_content_by_type(driver, selectors, content_type):
    """
    Extract specific type of content using multiple selectors.
    
    Args:
        driver (webdriver): Selenium WebDriver instance
        selectors (str or list): CSS selector(s) to find elements
        content_type (str): Type of content to extract
        
    Returns:
        list: Extracted content items
    """
    content = []
    if isinstance(selectors, str):
        selectors = [selectors]
        
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                if content_type == 'media':
                    for elem in elements:
                        src = elem.get_attribute('src')
                        if src:
                            content.append(src)
                elif content_type == 'embedded_links':
                    for elem in elements:
                        href = elem.get_attribute('href')
                        text = elem.text
                        if href:
                            content.append(f"{text}|{href}")
                else:
                    content.extend([elem.text for elem in elements if elem.text])
        except Exception as e:
            logger.error(f"Error extracting {content_type}: {e}")
            continue
            
    return content

def scrape_blog_content(driver):
    """
    Scrape content from current blog post page.
    
    Args:
        driver (webdriver): Selenium WebDriver instance
        
    Returns:
        bool: True if content was scraped and saved, False otherwise
    """
    try:
        site_type = get_site_specific_scraper(driver.current_url)
        selectors = CONFIG['SUPPORTED_SITES'].get(site_type, {})
        
        # Initialize content dictionary with all possible fields
        content = {col: '' for col in CONFIG['CSV_COLUMNS']}
        content.update({
            'url': driver.current_url,
            'timestamp': datetime.now().isoformat(),
            'site_type': site_type
        })

        # Wait for dynamic content
        t.sleep(CONFIG['POST_LOAD_TIME'])
        
        # Extract each type of content
        for field, field_selectors in selectors.items():
            try:
                extracted_content = extract_content_by_type(driver, field_selectors, field)
                if extracted_content:
                    if isinstance(extracted_content, list):
                        content[field] = '||'.join(extracted_content)
                    else:
                        content[field] = extracted_content
                        
                if field == 'media':
                    # Download media files
                    media_urls = []
                    for url in extracted_content:
                        saved_path = download_media(url, 'image')
                        if saved_path:
                            media_urls.append(saved_path)
                    content['media_urls'] = '||'.join(media_urls)
                    
            except Exception as e:
                logger.error(f"Error processing {field}: {e}")
                continue

        # Save content if essential fields are present
        if content.get('main_content') or content.get('title'):
            # Ensure CSV file exists
            csv_path = setup_csv_file()
            if csv_path:
                try:
                    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=CONFIG['CSV_COLUMNS'])
                        writer.writerow(content)
                    logger.info(f"Successfully saved content to {csv_path}")
                    return True
                except Exception as e:
                    logger.error(f"Error writing to CSV: {e}")
                    
        logger.warning("No significant content found to save")
        return False
        
    except Exception as e:
        logger.error(f"Error in content scraping: {e}")
        return False

def wait_for_search_results(driver):
    """
    Wait for search results to be visible after navigation.
    
    Args:
        driver (webdriver): Selenium WebDriver instance
        
    Returns:
        bool: True if results are found, False if timeout or error
    """
    try:
        site_type = get_site_specific_scraper(driver.current_url)
        selectors = CONFIG['SEARCH_RESULTS_SELECTORS'].get(site_type, ['.searchResults', 'article'])
        
        for selector in selectors:
            try:
                wait = WebDriverWait(driver, CONFIG['POST_LOAD_TIME'])
                results = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if results.is_displayed():
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        logger.error(f"Error waiting for search results: {e}")
        return False


def navigate_and_scrape_blog_posts(driver):
    """Navigate and scrape using PyAutoGUI image recognition approach."""
    try:
        posts_scraped = 0
        original_window = driver.current_window_handle
        
        # Try to open first post using PyAutoGUI image recognition
        if open_first_post_with_pyautogui(driver):
            try:
                # Wait for new tab to open
                t.sleep(CONFIG['TAB_LOAD_TIME'])
                
                # Switch to new tab
                new_window = driver.window_handles[-1]
                driver.switch_to.window(new_window)
                logger.info("Switched to new tab")
                
                # Scrape content
                if scrape_blog_content(driver):
                    posts_scraped += 1
                    logger.info("Successfully scraped post")
                
                # Close tab and return to original
                driver.close()
                driver.switch_to.window(original_window)
                
            except Exception as e:
                logger.error(f"Error processing post: {e}")
                if len(driver.window_handles) > 1:
                    driver.close()
                driver.switch_to.window(original_window)
        
        return posts_scraped
        
    except Exception as e:
        logger.error(f"Error in navigation: {e}")
        if driver.current_window_handle != original_window:
            driver.switch_to.window(original_window)
        return posts_scraped

def read_scraped_data():
    """Read and display scraped data from CSV file."""
    try:
        csv_path = Path(CONFIG['OUTPUT_DIR']) / 'scraped_data.csv'
        if not csv_path.exists():
            logger.error("No scraped data found")
            return None

        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                if df.empty:
                    logger.info("No data found in CSV file")
                    return None

                # Convert timestamp strings to datetime objects
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Get current session start time
                session_start = datetime.now().replace(microsecond=0) - pd.Timedelta(minutes=5)
                
                # Filter for entries from current session only
                current_entries = df[df['timestamp'] >= session_start]
                
                if current_entries.empty:
                    logger.info("No entries found from current session")
                    return None
                    
                print("\nScraped Data Summary (Current Session):")
                print(f"Entries in current session: {len(current_entries)}")
                print("\nCurrent session entries:")
                print(current_entries.to_string())
                return current_entries
                
            except UnicodeDecodeError:
                continue
                
        logger.error("Failed to read CSV with any encoding")
        return None
        
    except Exception as e:
        logger.error(f"Error reading scraped data: {e}")
        return None

def get_default_firefox_profile():
    """
    Get the specific Firefox profile path.
    
    Returns:
        str: Path to the specific profile
    """
    profile_path = os.path.join(
        CONFIG['FIREFOX_PROFILE_PATH'],
        CONFIG['SPECIFIC_PROFILE']
    )
    
    if os.path.exists(profile_path):
        logger.info(f"Using specific Firefox profile: {profile_path}")
        return profile_path
    else:
        logger.error(f"Specified profile not found at: {profile_path}")
        return None

def setup_firefox_driver():
    """
    Setup Firefox WebDriver using specific profile.
    
    Returns:
        webdriver or None: Configured Firefox WebDriver instance or None if error
    """
    try:
        options = FirefoxOptions()
        options.binary_location = CONFIG['FIREFOX_PATH']
        
        # Use specific profile
        profile_path = get_default_firefox_profile()
        if profile_path:
            options.add_argument('-profile')
            options.add_argument(profile_path)
            logger.info(f"Using Firefox profile: {profile_path}")
        else:
            logger.error("Specified profile not found, cannot continue")
            return None
        
        # Don't create new profile
        options.add_argument('--no-remote')
        options.add_argument('--new-window')
        
        # Disable private browsing
        options.set_preference("browser.privatebrowsing.autostart", False)
        
        # Use existing cookies and login data
        options.set_preference("privacy.clearOnShutdown.cookies", False)
        options.set_preference("privacy.clearOnShutdown.passwords", False)
        options.set_preference("signon.rememberSignons", True)
        
        service = FirefoxService(GeckoDriverManager().install())
        
        logger.info("Starting Firefox with specific profile")
        driver = webdriver.Firefox(
            service=service,
            options=options
        )
        return driver
        
    except Exception as e:
        logger.error(f"Error setting up Firefox driver: {e}")
        return None

def automate_search(url, purpose):
    """
    Automate search process using Selenium WebDriver.
    
    Args:
        url (str): Website URL to search
        purpose (str): Search query/purpose
        
    Returns:
        bool: True if search automation successful, False otherwise
    """
    try:
        if not check_browser_installed():
            return False
            
        driver = setup_firefox_driver()
        if not driver:
            return False
            
        try:
            # Navigate to URL
            driver.get(url)
            t.sleep(CONFIG['URL_LOAD_TIME'])
            
            search_bar = find_search_bar(driver)
            if search_bar:
                logger.info("Starting search process...")
                t.sleep(CONFIG['OPERATION_DELAY'])  # Add delay before search
                
                search_bar.clear()
                search_bar.send_keys(purpose)
                t.sleep(CONFIG['INPUT_DELAY'])
                search_bar.send_keys(Keys.RETURN)
                
                t.sleep(CONFIG['SEARCH_QUERY_WAIT_TIME'])
                
                posts_scraped = navigate_and_scrape_blog_posts(driver)
                logger.info(f"Successfully scraped {posts_scraped} posts")
                t.sleep(CONFIG['SCRAPING_COOLDOWN'])  # Add cooldown after scraping
                return True
            else:
                logger.error("Could not find search bar")
                return False
        finally:
            if driver:
                try:
                    t.sleep(CONFIG['OPERATION_DELAY'])  # Add delay before closing
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error closing driver: {e}")
    except Exception as e:
        logger.error(f"An error occurred during automation: {e}")
        return False

def main():
    """Main execution function with proper timing controls"""
    try:
        # Initial setup
        setup_directories()
        t.sleep(CONFIG['OPERATION_DELAY'])
        
        # User input phase
        user_input = pyautogui.prompt(text="Enter your query", title="Autoscrap")
        if not validate_input(user_input):
            logger.error("Invalid input provided")
            return False
        
        t.sleep(CONFIG['USER_INPUT_DELAY'])
        
        # Processing phase
        logger.info("Processing input...")
        website, purpose = extract_info(user_input)
        logger.info(f"Website: {website}")
        logger.info(f"Purpose: {purpose}")
        
        if website is None:
            logger.error("Unable to extract website from input")
            return False
        
        t.sleep(CONFIG['OPERATION_DELAY'])
        
        # Automation phase
        url = generate_url(website)
        logger.info(f"Generated URL: {url}")
        logger.info("Starting automation process...")
        
        t.sleep(CONFIG['OPERATION_DELAY'])
        success = automate_search(url, purpose)
        
        # Results phase
        if success:
            t.sleep(CONFIG['FINAL_DISPLAY_DELAY'])
            logger.info("Preparing to display results...")
            read_scraped_data()
            
        return success
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        return False
    finally:
        logger.info("Process completed")

if __name__ == "__main__":
    main()





