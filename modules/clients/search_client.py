import asyncio
import aiohttp
import requests
import urllib.parse
import json
from bs4 import BeautifulSoup
from typing import List, Dict
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.rate_limiter import RateLimitHandler
from playwright.sync_api import sync_playwright
import random
def load_api_keys():
    config_file = 'config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

api_keys = load_api_keys()
google_cse_keys = api_keys.get("google_cse", [])

class SearchClient:
    def __init__(self, rate_limiter: RateLimitHandler):
        self.rate_limiter = rate_limiter
        self.cse_fallback_count = 0
        self.visited_search_queries = set()
    
    async def google_search(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:
        try:
            if len(query) > 150:
                shortened_query = ' '.join(query.split()[:10])  # Take first 10 words
                buffer.add_log(f"Query too long, shortening from '{query}' to '{shortened_query}'", high_level=True)
                query = shortened_query
            if any(academic_term in query.lower() for academic_term in 
                ['filetype:pdf', 'site:.edu', 'site:.ac', 'site:arxiv', 'methodology', 'research']):
                if query in self.visited_search_queries:
                    query_parts = query.split()
                    if 'filetype:pdf' in query:
                        academic_modifier = "recent academic"
                        modified_query = f"{' '.join(query_parts[:3])} {academic_modifier}"
                        if 'filetype:pdf' not in modified_query:
                            modified_query += " filetype:pdf"
                    else:
                        modified_query = f"{' '.join(query_parts[:3])} methodology"
                        
                    buffer.add_log(f"Modifying academic query from '{query}' to '{modified_query}'", high_level=True)
                    query = modified_query
            elif query in self.visited_search_queries:
                query_parts = query.split()
                if len(query_parts) > 3:
                    modified_query = ' '.join(query_parts[:3]) + " alternative perspective"
                else:
                    modified_query = f"{query} alternative perspective"
                    
                buffer.add_log(f"Already searched for '{query}', trying alternative: '{modified_query}'", high_level=True)
                query = modified_query
                
            self.visited_search_queries.add(query)
            buffer.add_log(f"Performing Google search for: {query}", high_level=True)
            
            if self.cse_fallback_count >= 3:
                buffer.add_log("Using alternative search engines due to previous CSE failures", high_level=True)
                return await self.combined_search(query, buffer)
            
            retry_count = 0
            max_retries = 2
            
            while retry_count < max_retries:
                try:
                    await self.rate_limiter.wait_if_needed("google_cse")
                    
                    async with aiohttp.ClientSession() as session:
                        search_url = "https://www.googleapis.com/customsearch/v1"
                        selected_key = random.choice(google_cse_keys)
                        params = {
                            "key": selected_key["cse_api"],
                            "cx": selected_key["cseid"],
                            "q": query,
                            "num": 10
                        }
                        
                        if buffer.verbose:
                            buffer.add_log(f"Sending request to Google CSE API")
                        
                        async with session.get(search_url, params=params) as response:
                            if response.status == 429:
                                retry_count += 1
                                backoff_time = retry_count * 5
                                
                                if retry_count < max_retries:
                                    buffer.add_log(f"Google CSE API rate limit hit, retrying in {backoff_time}s (attempt {retry_count}/{max_retries})")
                                    await asyncio.sleep(backoff_time)
                                    continue
                                else:
                                    buffer.add_log(f"Google CSE API rate limit exceeded after {max_retries} attempts. Falling back to alternatives.", high_level=True)
                                    self.cse_fallback_count += 1
                                    return await self.combined_search(query, buffer)
                            
                            elif response.status != 200:
                                buffer.add_log(f"Google CSE API error: {response.status}")
                                self.cse_fallback_count += 1
                                return await self.combined_search(query, buffer)
                            
                            data = await response.json()
                            if "items" not in data:
                                buffer.add_log("No Google search results found")
                                return await self.combined_search(query, buffer)
                            
                            if buffer.verbose:
                                buffer.add_log(f"Received {len(data['items'])} Google search results")
                            
                            results = []
                            for item in data["items"]:
                                results.append({
                                    "title": item.get("title", ""),
                                    "link": item.get("link", ""),
                                    "snippet": item.get("snippet", "")
                                })
                            
                            if results:
                                self.cse_fallback_count = 0
                                
                            return results
                
                except aiohttp.ClientError as e:
                    buffer.add_log(f"Google CSE API client error: {str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        return await self.combined_search(query, buffer)
                    
        except Exception as e:
            buffer.add_log(f"Error in Google search: {str(e)}", high_level=True)
            return await self.combined_search(query, buffer)
    
    async def research_google_search(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:
        try:
            if query in self.visited_search_queries:
                modified_query = f"{query} research details"
                buffer.add_log(f"Already searched for '{query}', trying alternative: '{modified_query}'", high_level=True)
                query = modified_query
            
            self.visited_search_queries.add(query)
            buffer.add_log(f"Performing research-focused Google search for: {query}", high_level=True)
            
            if self.cse_fallback_count >= 3:
                buffer.add_log("Using alternative search engines due to previous CSE failures", high_level=True)
                return await self.combined_search(query, buffer)
            
            retry_count = 0
            max_retries = 2
            
            while retry_count < max_retries:
                try:
                    await self.rate_limiter.wait_if_needed("google_cse")
                    
                    async with aiohttp.ClientSession() as session:
                        search_url = "https://www.googleapis.com/customsearch/v1"
                        selected_key = random.choice(google_cse_keys)
                        params = {
                            "key": selected_key["cse_api"],
                            "cx": selected_key["cseid"],
                            "q": query,
                            "num": 5
                        }
                        
                        if buffer.verbose:
                            buffer.add_log(f"Sending request to Google Research CSE API")
                        
                        async with session.get(search_url, params=params) as response:
                            if response.status == 429:
                                retry_count += 1
                                backoff_time = retry_count * 5
                                
                                if retry_count < max_retries:
                                    buffer.add_log(f"Google CSE API rate limit hit, retrying in {backoff_time}s (attempt {retry_count}/{max_retries})")
                                    await asyncio.sleep(backoff_time)
                                    continue
                                else:
                                    buffer.add_log(f"Google CSE API rate limit exceeded after {max_retries} attempts. Falling back to DuckDuckGo.", high_level=True)
                                    self.cse_fallback_count += 1
                                    return await self.combined_search(query, buffer)
                            
                            elif response.status != 200:
                                buffer.add_log(f"Google Research CSE API error: {response.status}")
                                self.cse_fallback_count += 1
                                return await self.combined_search(query, buffer)
                            
                            data = await response.json()
                            if "items" not in data:
                                buffer.add_log("No Google research search results found")
                                return await self.combined_search(query, buffer)
                            
                            if buffer.verbose:
                                buffer.add_log(f"Received {len(data['items'])} Google research search results")
                            
                            results = []
                            for item in data["items"]:
                                results.append({
                                    "title": item.get("title", ""),
                                    "link": item.get("link", ""),
                                    "snippet": item.get("snippet", "")
                                })
                            
                            if results:
                                self.cse_fallback_count = 0
                                
                            return results
                            
                except aiohttp.ClientError as e:
                    buffer.add_log(f"Google CSE API client error: {str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        return await self.combined_search(query, buffer)
                    
        except Exception as e:
            buffer.add_log(f"Error in Google research search: {str(e)}", high_level=True)
            return await self.combined_search(query, buffer)
    
    async def duckduckgo_lite_search(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:
        try:
            buffer.add_log(f"Using DuckDuckGo Lite search fallback for: {query}", high_level=True)
            await self.rate_limiter.wait_if_needed("duckduckgo")
            
            url = "https://lite.duckduckgo.com/lite/"
            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            }
            data = {"q": query}
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.post(url, headers=headers, data=data)
            )
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            results = []
            for i, tr in enumerate(soup.find_all("tr")):
                if i > 30:
                    break
                    
                a_tags = tr.find_all("a")
                for a_tag in a_tags:
                    if a_tag and "href" in a_tag.attrs and a_tag.get_text().strip():
                        link = a_tag["href"]
                        if not link.startswith(("http://", "https://")):
                            continue
                            
                        snippet = ""
                        next_tr = tr.find_next_sibling("tr")
                        if next_tr:
                            snippet = next_tr.get_text().strip()
                            
                        title = a_tag.get_text().strip()
                        if title and link:
                            results.append({
                                "title": title,
                                "link": link,
                                "snippet": snippet
                            })
                            
                        if len(results) >= 10:
                            break
                            
            buffer.add_log(f"Found {len(results)} results from DuckDuckGo Lite", high_level=True)
            return results
            
        except Exception as e:
            buffer.add_log(f"Error with DuckDuckGo Lite search: {str(e)}", high_level=True)
            return []
    
    async def brave_search(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:

        try:
            buffer.add_log(f"Using Playwright-based Brave search for: {query}", high_level=True)
            await self.rate_limiter.wait_if_needed("brave")
            loop = asyncio.get_event_loop()
            encoded_query = urllib.parse.quote(query)
            result_urls = await loop.run_in_executor(None, lambda: self._run_brave_playwright(encoded_query))
            
            if not result_urls:
                buffer.add_log("No results found from Brave search, trying fallback method")
                return await self._brave_search_fallback(query, buffer)
            results = []
            for url in result_urls[:10]:  # Limit to top 10 results
                title = self._extract_title_from_url(url) 
                results.append({
                    "title": title,
                    "link": url,
                    "snippet": f"Result found on {self._extract_domain_from_url(url)}",
                    "source": "brave_playwright"
                })
                
            buffer.add_log(f"Found {len(results)} results from Playwright Brave search", high_level=True)
            return results
                
        except Exception as e:
            buffer.add_log(f"Error with Playwright Brave search: {str(e)}", high_level=True)
            return await self._brave_search_fallback(query, buffer)

    def _run_brave_playwright(self, query):

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_timeout(30000)  # 30 seconds
                page.goto(f"https://search.brave.com/search?q={query}")
                
                try:
                    page.wait_for_selector('.snippet, .result')
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    results = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith("http") and not any(x in href for x in ['brave.com', 'search.brave', 'bing.com']):
                            results.append(href)
                            
                except Exception as e:
                    print(f"Error waiting for Brave results: {str(e)}")
                    return []
                
                finally:
                    browser.close()
                return list(dict.fromkeys(results))
                
        except Exception as e:
            print(f"Error in Playwright Brave search: {str(e)}")
            return []

    async def _brave_search_fallback(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:

        try:
            buffer.add_log(f"Using fallback Brave search for: {query}", high_level=True)
            await self.rate_limiter.wait_if_needed("brave")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Encoding": "gzip, deflate"
            }
            
            search_url = f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(search_url, headers=headers)
            )
            
            if response.status_code != 200:
                buffer.add_log(f"Brave search error: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            search_results = soup.select("div.snippet")
            
            if not search_results:
                search_results = soup.select("div.result")
            
            for result in search_results[:10]:  # Limit to first 10 results
                title_elem = result.select_one("a.title")
                snippet_elem = result.select_one("div.snippet-description")
                link_elem = result.select_one("a.result-header")
                
                title = title_elem.get_text().strip() if title_elem else ""
                snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                link = link_elem.get("href") if link_elem else None
                
                if not title or not link or not link.startswith(("http://", "https://")):
                    continue
                
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "source": "brave_fallback"
                })
            if not results:
                buffer.add_log("Using fallback link extraction for Brave search")
                for link in soup.find_all("a"):
                    href = link.get("href")
                    text = link.get_text().strip()
                    if (href and href.startswith(("http://", "https://")) and 
                        text and len(text) > 10 and 
                        "brave.com" not in href and 
                        "favicon" not in href):
                        
                        results.append({
                            "title": text[:100],
                            "link": href,
                            "snippet": "",
                            "source": "brave_fallback"
                        })
                        
                        if len(results) >= 10:
                            break
            
            buffer.add_log(f"Found {len(results)} results from Brave fallback search", high_level=True)
            return results
                
        except Exception as e:
            buffer.add_log(f"Error with Brave fallback search: {str(e)}", high_level=True)
            return []
    
    async def bing_search(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:

        try:
            buffer.add_log(f"Using Playwright-based Bing search for: {query}", high_level=True)
            await self.rate_limiter.wait_if_needed("bing")
            loop = asyncio.get_event_loop()
            encoded_query = urllib.parse.quote(query)
            result_urls = await loop.run_in_executor(None, lambda: self._run_bing_playwright(encoded_query))
            
            if not result_urls:
                buffer.add_log("No results found from Bing search, trying fallback method")
                return await self._bing_search_fallback(query, buffer)
            results = []
            for url in result_urls[:10]:  # Limit to top 10 results
                title = self._extract_title_from_url(url) 
                results.append({
                    "title": title,
                    "link": url,
                    "snippet": f"Result found on {self._extract_domain_from_url(url)}",
                    "source": "bing_playwright"
                })
                
            buffer.add_log(f"Found {len(results)} results from Playwright Bing search", high_level=True)
            return results
                
        except Exception as e:
            buffer.add_log(f"Error with Playwright Bing search: {str(e)}", high_level=True)
            return await self._bing_search_fallback(query, buffer)
    
    def _run_bing_playwright(self, query):

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_timeout(30000)  # 30 seconds
                page.goto(f"https://www.bing.com/search?q={query}")
                
                try:
                    page.wait_for_selector('ol#b_results')
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    results = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith("http") and not any(x in href for x in ['microsoft.com', 'bing.com', 'msn.com', 'windows.com']):
                            results.append(href)
                            
                except Exception as e:
                    print(f"Error waiting for Bing results: {str(e)}")
                    return []
                
                finally:
                    browser.close()
                return list(dict.fromkeys(results))
                
        except Exception as e:
            print(f"Error in Playwright Bing search: {str(e)}")
            return []
    
    async def _bing_search_fallback(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:

        try:
            buffer.add_log(f"Using fallback Bing search for: {query}", high_level=True)
            await self.rate_limiter.wait_if_needed("bing")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.bing.com/search?q={encoded_query}"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(search_url, headers=headers, timeout=10)
            )
            
            if response.status_code != 200:
                buffer.add_log(f"Bing fallback search error: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text().strip()
                
                if (href.startswith(("http://", "https://")) and 
                    len(text) > 5 and 
                    not any(domain in href.lower() for domain in ['bing.com', 'microsoft.com', 'msn.com'])):
                    
                    results.append({
                        "title": text[:100] if text else self._extract_domain_from_url(href),
                        "link": href,
                        "snippet": "",
                        "source": "bing_fallback"
                    })
                    
                    if len(results) >= 10:
                        break
            
            buffer.add_log(f"Found {len(results)} results from Bing fallback search", high_level=True)
            return results
            
        except Exception as e:
            buffer.add_log(f"Error with Bing fallback search: {str(e)}", high_level=True)
            return []
    
    def _extract_domain_from_url(self, url):

        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return "Unknown Source"
    
    def _extract_title_from_url(self, url):

        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            if path.endswith(('.html', '.htm', '.php', '.asp', '.aspx')):
                path = path.rsplit('.', 1)[0]
            segments = [s for s in path.split('/') if s]
            if segments:
                title = segments[-1].replace('-', ' ').replace('_', ' ').title()
                return title
            domain = self._extract_domain_from_url(url)
            return f"Content from {domain}"
        except:
            return "Search Result"
    
    async def combined_search(self, query: str, buffer: AsyncBuffer) -> List[Dict[str, str]]:

        try:
            if len(query) > 150:
                shortened_query = ' '.join(query.split()[:10])  # Take first 10 words
                buffer.add_log(f"Query too long, shortening from '{query}' to '{shortened_query}'", high_level=True)
                query = shortened_query
                
            buffer.add_log(f"Performing combined search for: {query}", high_level=True)
            bing_results_task = asyncio.create_task(self.bing_search(query, buffer))
            brave_results_task = asyncio.create_task(self.brave_search(query, buffer))
            duck_results_task = asyncio.create_task(self.duckduckgo_lite_search(query, buffer))
            bing_results, brave_results, duck_results = await asyncio.gather(
                bing_results_task, brave_results_task, duck_results_task
            )
            combined_results = []
            seen_urls = set()
            for source_name, results in [("Bing", bing_results), 
                                        ("DuckDuckGo", duck_results), 
                                        ("Brave", brave_results)]:
                for result in results:
                    url = result.get("link", "")
                    if not url or url in seen_urls:
                        continue
                    title = result.get("title", "").strip()
                    if not title or len(title) < 5:
                        continue
                    skip_keywords = ["login", "sign up", "register", "shopping", "buy now", "promotion",
                                    "% off", "discount", "free", "shipping", "add to cart"]
                    if any(keyword in title.lower() for keyword in skip_keywords):
                        continue
                    if not url.startswith(("http://", "https://")):
                        continue
                    seen_urls.add(url)
                    combined_results.append({
                        "title": title,
                        "link": url,
                        "snippet": result.get("snippet", f"Result from {source_name}"),
                        "source": source_name.lower()
                    })
            
            buffer.add_log(f"Combined search found {len(combined_results)} unique results", high_level=True)
            return combined_results[:10]  # Limit to top 10 results
            
        except Exception as e:
            buffer.add_log(f"Error in combined search: {str(e)}", high_level=True)
            return await self.duckduckgo_lite_search(query, buffer)
