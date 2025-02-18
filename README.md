# SmartScrapper

An automated web scraping tool that uses PyAutoGUI and Selenium to interact with web pages, perform searches, and scrape content.

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
1. Run the script:
   ```sh
   python au.py
   ```

2. Follow the prompts to enter your query.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.