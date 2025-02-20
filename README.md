# SmartScrapper

An automated web scraping tool that uses PyAutoGUI and Selenium to interact with web pages, perform searches, and scrape content.
currently focuses on Medium.com. X.com(Twitter) support is planned for future releases.

## Features
- Automated UI Interaction
  - Clicking
  - Typing
  - Scrolling
  - Switching windows
- Task Context Maintenance
  - Maintains task state across multiple actions
  - Retries automatically if a previous action fails
- Smart Error Handling
  - Prevents crashes by detecting UI changes dynamically

## Requirements
- Python 3.x
- PyAutoGUI
- Selenium
- SpaCy
- BeautifulSoup4
- Requests
- WebDriver Manager
-pandas
- spacy
-hashlib
-cv2

## Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/your-username/SmartScrapper.git
   cd SmartScrapper
   ```

2. Install the required packages:
   ```sh
   pip install -r requirements.txt
   ```

## Usage
## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt

2. Run the script:
   ```sh
   python au.py
   ```

3. Follow the prompts to enter your query.

e.g., "app ideas 2025"—the scraper will search and scrape posts from Medium.com.
```markdown
## Known Limitations

- The current version only supports scraping from Medium.com.
- Some visual selectors may need updating if Medium.com changes its layout.
- CSV output format is subject to change based on extracted data.

## Future Enhancements

- Add Twitter scraping functionality.
- Improve error handling and dynamic selector matching.
- Enhance CSV formatting and data sanitization.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.