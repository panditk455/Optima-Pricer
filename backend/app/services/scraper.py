import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
import json
import urllib.parse
import time

# Selenium for JavaScript rendering 
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[Scraper] WARNING: Selenium not installed. Install with: pip install selenium webdriver-manager")


class ScrapedPrice:
    def __init__(self, price: float, source: str, url: str):
        self.price = price
        self.source = source
        self.url = url


class MarketDataScraper:
    """Google Shopping scraper using Selenium + BeautifulSoup
    
    This scraper uses Selenium to render JavaScript and BeautifulSoup
    to extract prices from Google Shopping search results.
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 1 hour
        self.driver = None
    
    def _get_driver(self):
        """Get or create Selenium WebDriver"""
        if not SELENIUM_AVAILABLE:
            return None
        
        if self.driver is None:
            try:
                import os
                import stat
                import platform
                
                chrome_options = Options()
                chrome_bin = os.getenv("CHROME_BIN")
                if chrome_bin:
                    chrome_options.binary_location = chrome_bin

                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-software-rasterizer')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                # On macOS, specify Chrome binary path
                if platform.system() == 'Darwin':
                    chrome_binary = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                    if os.path.exists(chrome_binary):
                        chrome_options.binary_location = chrome_binary
                        print(f'[Scraper] Using Chrome binary: {chrome_binary}')
                
                # Try to install and use ChromeDriver
                try:
                    driver_env = os.getenv("CHROMEDRIVER")
                    
                    if driver_env and os.path.exists(driver_env):
                        service = Service(driver_env)
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        driver_path = ChromeDriverManager().install()
                    
        
                    print(f'[Scraper] ChromeDriver path: {driver_path}')
                    
                    # Make sure it's executable
                    if os.path.exists(driver_path):
                        os.chmod(driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                        print(f'[Scraper] ChromeDriver permissions set')
                    
                    service = Service(driver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    
                    # Set timeouts
                    self.driver.set_page_load_timeout(30)
                    self.driver.implicitly_wait(5)
                    
                    # Execute CDP commands to avoid detection
                    self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                        'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                        '''
                    })
                    print(f'[Scraper] WebDriver created successfully')
                except Exception as driver_error:
                    print(f'[Scraper] Error setting up ChromeDriver: {driver_error}')
                    import traceback
                    traceback.print_exc()
                    # Try without specifying path (use system ChromeDriver)
                    try:
                        print(f'[Scraper] Trying system ChromeDriver...')
                        self.driver = webdriver.Chrome(options=chrome_options)
                        self.driver.set_page_load_timeout(30)
                        self.driver.implicitly_wait(5)
                        print(f'[Scraper] System ChromeDriver worked')
                    except Exception as system_error:
                        print(f'[Scraper] System ChromeDriver also failed: {system_error}')
                        import traceback
                        traceback.print_exc()
                        return None
            except Exception as e:
                print(f'[Scraper] Error creating WebDriver: {e}')
                import traceback
                traceback.print_exc()
                return None
        
        return self.driver
    
    def __del__(self):
        """Clean up WebDriver on deletion"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def _get_cached(self, key: str) -> Optional[List[ScrapedPrice]]:
        """Get cached data if still valid"""
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                return cached_data
        return None
    
    def _set_cache(self, key: str, data: List[ScrapedPrice]):
        """Cache scraped data"""
        self.cache[key] = (data, datetime.now())
    
    def _extract_retailer_name(self, url: str) -> str:
        """Extract retailer name from URL"""
        url_lower = url.lower()
        
        retailers = {
            'amazon': ['amazon.com', 'amazon'],
            'walmart': ['walmart.com', 'walmart'],
            'target': ['target.com', 'target'],
            'bestbuy': ['bestbuy.com', 'best buy'],
            'homedepot': ['homedepot.com', 'home depot'],
            'lowes': ['lowes.com', 'lowes'],
            'wayfair': ['wayfair.com', 'wayfair'],
            'ebay': ['ebay.com', 'ebay'],
            'etsy': ['etsy.com', 'etsy'],
            'costco': ['costco.com', 'costco'],
            'newegg': ['newegg.com', 'newegg'],
        }
        
        for retailer, patterns in retailers.items():
            for pattern in patterns:
                if pattern in url_lower:
                    return retailer
        
        return 'google_shopping'
    
    def _get_min_price_for_product(self, product_name: str, category: Optional[str] = None) -> float:
        """Get minimum expected price based on product name"""
        name_lower = product_name.lower()
        
        # High-end phones
        if 'iphone' in name_lower:
            if any(kw in name_lower for kw in ['pro max', '1tb', '512gb']):
                return 1000.0
            elif 'pro' in name_lower:
                return 800.0
            return 500.0
        
        # Other premium electronics
        if any(kw in name_lower for kw in ['samsung galaxy', 'ultra', 'fold']):
            return 800.0
        
        # Standard electronics
        if category and 'electronic' in category.lower():
            return 50.0
        
        return 10.0
    
    def scrape_google_shopping(self, product_name: str, category: Optional[str] = None) -> List[ScrapedPrice]:
        """Scrape Google Shopping using Selenium + BeautifulSoup"""
        # Improve search query
        search_query = product_name.strip()
        name_lower = product_name.lower()
        
        # For phones, add "unlocked" and "new" to get actual products
        if 'iphone' in name_lower or 'samsung' in name_lower:
            if 'unlocked' not in search_query.lower():
                search_query = f"{search_query} unlocked"
            if 'new' not in search_query.lower():
                search_query = f"new {search_query}"
        
        if category:
            search_query = f"{search_query} {category}"
        
        url = f"https://www.google.com/search?tbm=shop&q={search_query.replace(' ', '+')}"
        
        print(f'[Scraper] Scraping Google Shopping for: {product_name}')
        prices = []
        
        # Use Selenium to render JavaScript
        driver = self._get_driver()
        if not driver:
            print(f'[Scraper] ERROR: Selenium WebDriver not available')
            return []
        
        try:
            print(f'[Scraper] Loading page with Selenium...')
            driver.get(url)
            
            # Wait for shopping results to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-docid], .sh-dgr__content, div.g"))
                )
                time.sleep(2)  # Give it a moment for prices to render
            except:
                print(f'[Scraper] Waiting for page elements...')
                time.sleep(3)
            
            # Scroll to load more results
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Get the rendered HTML
            html_content = driver.page_source
            print(f'[Scraper] Got HTML: {len(html_content)} chars')
            
            # Extract prices using BeautifulSoup
            print(f'[Scraper] Extracting prices with BeautifulSoup...')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            min_price = self._get_min_price_for_product(product_name, category)
            
            # Look for JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    items = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
                    for item in items:
                        if isinstance(item, dict) and ('Product' in str(item.get('@type', ''))):
                            offers = item.get('offers', {})
                            if isinstance(offers, list) and len(offers) > 0:
                                offers = offers[0]
                            if isinstance(offers, dict):
                                price = offers.get('price')
                                if price:
                                    try:
                                        price_val = float(str(price).replace(',', ''))
                                        if price_val >= min_price and 10.0 <= price_val <= 100000:
                                            url_val = offers.get('url') or item.get('url') or url
                                            retailer = self._extract_retailer_name(url_val)
                                            prices.append(ScrapedPrice(price_val, retailer, url_val))
                                            print(f'[Scraper] JSON-LD found: ${price_val:.2f} from {retailer}')
                                    except (ValueError, TypeError):
                                        continue
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # Extract prices from HTML elements - try multiple approaches
            # Google Shopping uses various structures, so we'll try many selectors
            
            # Approach 1: Look for shopping result containers
            product_containers = (
                soup.select('div[data-docid]') +
                soup.select('.sh-dgr__content') +
                soup.select('div.g[data-hveid]') +
                soup.select('div[data-ved]') +
                soup.select('.sh-dgr__grid-result') +
                soup.select('div.g')
            )
            
            print(f'[Scraper] Found {len(product_containers)} potential product containers')
            
            # Track seen prices to avoid duplicates
            seen_prices = set()
            
            # Process more containers (up to 200)
            for container in product_containers[:200]:
                try:
                    # Try multiple price selectors (Google Shopping uses various classes)
                    price_elem = None
                    price_selectors = [
                        '.a8Pemb',           # Common Google Shopping price class
                        '[data-price]',      # Data attribute
                        '.price',            # Generic price class
                        '.Nr22bf',           # Another Google Shopping class
                        '.a-price-whole',    # Amazon-style
                        '.a-price',          # Amazon-style
                        '.TK6gbf',           # Google Shopping variant
                        '.b8vIg',            # Google Shopping price
                        'span[aria-label*="$"]',  # Aria label with price
                        '[class*="price"]',   # Any class with "price"
                        '[class*="Price"]',   # Case variant
                        'span[class*="a8Pemb"]',  # Span variant
                        'div[class*="price"]',   # Div variant
                    ]
                    
                    for selector in price_selectors:
                        price_elem = container.select_one(selector)
                        if price_elem:
                            break
                    
                    # Extract price from element or container text
                    price_val = None
                    container_text = container.get_text()
                    
                    # First try price element
                    if price_elem:
                        price_text = price_elem.get_text()
                        price_match = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text.replace(',', ''))
                        if price_match:
                            price_val = float(price_match.group(1).replace(',', ''))
                    
                    # If no price from element, search container text
                    if not price_val:
                        # Look for all price patterns in container text
                        price_matches = re.findall(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', container_text)
                        if price_matches:
                            # Take the largest price (usually the product price, not shipping)
                            for price_str in sorted(price_matches, key=lambda x: float(x.replace(',', '')), reverse=True):
                                try:
                                    candidate_price = float(price_str.replace(',', ''))
                                    if candidate_price >= min_price and 10.0 <= candidate_price <= 100000:
                                        price_val = candidate_price
                                        break
                                except ValueError:
                                    continue
                    
                    # If we found a valid price, add it
                    if price_val and price_val >= min_price and 10.0 <= price_val <= 100000:
                        # Create a unique key for deduplication
                        price_key = (round(price_val, 2),)
                        
                        # Find link in container
                        link = container.find('a', href=True)
                        product_url = url
                        if link:
                            href = link.get('href', '')
                            if href.startswith('/url?'):
                                url_match = re.search(r'url=([^&]+)', href)
                                if url_match:
                                    product_url = urllib.parse.unquote(url_match.group(1))
                            elif href.startswith('http'):
                                product_url = href
                        
                        retailer = self._extract_retailer_name(product_url)
                        
                        # Avoid duplicates (same price from same retailer)
                        dedup_key = (round(price_val, 2), retailer)
                        if dedup_key not in seen_prices:
                            seen_prices.add(dedup_key)
                            prices.append(ScrapedPrice(price_val, retailer, product_url))
                            print(f'[Scraper] Found: ${price_val:.2f} from {retailer}')
                            
                except Exception as e:
                    continue
            
            # Approach 2: Search for all price patterns in the HTML
            if len(prices) < 5:
                print(f'[Scraper] Searching for price patterns in HTML...')
                # Find all elements that might contain prices
                all_elements = soup.find_all(['span', 'div', 'p', 'td', 'li'])
                for elem in all_elements[:200]:
                    try:
                        text = elem.get_text()
                        # Look for price patterns
                        price_matches = re.findall(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
                        for price_str in price_matches:
                            try:
                                price_val = float(price_str.replace(',', ''))
                                if price_val >= min_price and 10.0 <= price_val <= 100000:
                                    # Try to find associated link
                                    parent = elem.find_parent()
                                    link = None
                                    if parent:
                                        link = parent.find('a', href=True)
                                    if not link:
                                        link = elem.find('a', href=True)
                                    
                                    product_url = url
                                    if link:
                                        href = link.get('href', '')
                                        if href.startswith('/url?'):
                                            url_match = re.search(r'url=([^&]+)', href)
                                            if url_match:
                                                product_url = urllib.parse.unquote(url_match.group(1))
                                        elif href.startswith('http'):
                                            product_url = href
                                    
                                    retailer = self._extract_retailer_name(product_url)
                                    # Avoid duplicates
                                    if not any(abs(p.price - price_val) < 1.0 and p.source == retailer for p in prices):
                                        prices.append(ScrapedPrice(price_val, retailer, product_url))
                                        print(f'[Scraper] Found (pattern): ${price_val:.2f} from {retailer}')
                            except ValueError:
                                continue
                    except:
                        continue
            
            # Fallback: Extract prices using regex from raw HTML if we still don't have enough
            if len(prices) < 5:
                print(f'[Scraper] Trying regex extraction from raw HTML...')
                # More comprehensive price patterns - look for prices in context
                # Find prices that appear near product-related keywords
                price_context_pattern = re.compile(
                    r'(?:price|cost|buy|shop|from|only|now|save|sale|deal)[\s:]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                    re.IGNORECASE
                )
                price_matches = price_context_pattern.findall(html_content)
                
                # Also get standalone prices
                standalone_prices = re.findall(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', html_content)
                
                # Combine and deduplicate
                all_price_strings = list(set(price_matches + standalone_prices))
                
                for price_str in all_price_strings[:150]:
                    try:
                        price_val = float(price_str.replace(',', ''))
                        if price_val >= min_price and 10.0 <= price_val <= 100000:
                            # Avoid duplicates
                            dedup_key = (round(price_val, 2), 'google_shopping')
                            if dedup_key not in seen_prices:
                                seen_prices.add(dedup_key)
                                retailer = self._extract_retailer_name(url)
                                prices.append(ScrapedPrice(price_val, retailer, url))
                                print(f'[Scraper] Regex found: ${price_val:.2f} from {retailer}')
                                if len(prices) >= 20:  # Limit to 20 prices
                                    break
                    except ValueError:
                        continue
            
        except Exception as e:
            print(f'[Scraper] Error during scrape: {e}')
            import traceback
            traceback.print_exc()
            return []
        
        # Deduplicate
        seen = set()
        unique_prices = []
        for p in prices:
            key = (p.price, p.source)
            if key not in seen:
                seen.add(key)
                unique_prices.append(p)
        
        return unique_prices[:20]
    
    def scrape_all_sources(self, product_name: str, category: Optional[str] = None, force_refresh: bool = False) -> List[ScrapedPrice]:
        """Scrape Google Shopping to get prices from all retailers
        
        This is the main method - uses BeautifulSoup for HTML parsing
        
        Args:
            product_name: Name of the product to search for
            category: Optional product category
            force_refresh: If True, bypass cache and perform fresh scrape
        """
        cache_key = f"{product_name}_{category or ''}"
        
        # Check cache only if not forcing refresh
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached:
                print(f'[Scraper] Using cached data for: {product_name}')
                return cached
        else:
            print(f'[Scraper] Force refresh requested - bypassing cache for: {product_name}')
            # Clear cache for this key if it exists
            if cache_key in self.cache:
                del self.cache[cache_key]
        
        print(f'[Scraper] Starting fresh scrape for: {product_name} ({category or "N/A"})')
        print(f'[Scraper] Using Selenium + BeautifulSoup to get prices from all retailers shown in Google Shopping')
        
        # Scrape Google Shopping
        all_prices = self.scrape_google_shopping(product_name, category)
        
        # Cache results
        self._set_cache(cache_key, all_prices)
        
        # Print summary
        print(f'\n[Scraper] ===== SCRAPING SUMMARY =====')
        print(f'[Scraper] Total prices collected: {len(all_prices)}')
        
        if all_prices:
            from collections import defaultdict
            prices_by_source = defaultdict(list)
            for p in all_prices:
                prices_by_source[p.source].append(p.price)
            
            print(f'[Scraper] Prices by retailer:')
            for source, prices_list in sorted(prices_by_source.items()):
                avg = sum(prices_list) / len(prices_list)
                print(f'  {source}: {len(prices_list)} prices, avg ${avg:.2f}')
        
        print(f'[Scraper] =============================')
        
        return all_prices
    
    @staticmethod
    def calculateAveragePrice(prices: List[ScrapedPrice]) -> Optional[float]:
        """Calculate average price from scraped prices"""
        if not prices:
            return None
        
        valid_prices = [p.price for p in prices if p.price > 0]
        if not valid_prices:
            return None
        
        return sum(valid_prices) / len(valid_prices)
    
    @staticmethod
    def get_price_range(prices: List[ScrapedPrice]) -> Optional[Dict[str, float]]:
        """Get price range (min/max) from scraped prices"""
        if not prices:
            return None
        
        valid_prices = [p.price for p in prices if p.price > 0]
        if not valid_prices:
            return None
        
        return {
            'min': min(valid_prices),
            'max': max(valid_prices)
        }


# Singleton instance
scraper = MarketDataScraper()
