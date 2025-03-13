import time
from typing import Dict, Any, Callable
from urllib.parse import urlparse

class URLTracker:

    
    def __init__(self):
        self.reset_tracking()
        
    def reset_tracking(self):

        self.url_tracking = {
            "total_urls_scraped": 0,
            "total_urls_tracked": 0,
            "wikipedia_count": 0,
            "arxiv_count": 0,
            "academic_pdf_count": 0,
            "news_count": 0, 
            "stats_sources_count": 0,
            "doi_papers_count": 0,
            "web_page_count": 0,
            "failed_scrapes": 0,
            "arxiv_papers_count": 0,  # Additional counter specific to arxiv
            "url_sources": {},  # Domain -> count
            "last_updated": time.time()
        }
        return self.url_tracking
    
    def get_tracking_data(self):

        return self.url_tracking
    
    def setup_tracking_for_scraper(self, web_scraper, research_data, save_callback):

        if hasattr(web_scraper, 'scrape_url'):
            original_scrape_method = web_scraper.scrape_url
            
            async def tracked_scrape_url(url, buffer, **kwargs):
                self.url_tracking['total_urls_tracked'] += 1
                self.url_tracking['total_urls_scraped'] += 1
                try:
                    domain = urlparse(url).netloc
                    self.url_tracking['url_sources'][domain] = self.url_tracking['url_sources'].get(domain, 0) + 1
                except:
                    pass
                    
                try:
                    content = await original_scrape_method(url, buffer, **kwargs)
                    if content:
                        self._classify_and_count_url(url, buffer)
                        research_data["url_tracking"] = self.url_tracking
                        save_callback()
                        if buffer:
                            buffer.add_log(f"Scraped URL: {url} (Total URLs: {self.url_tracking['total_urls_scraped']})", high_level=True)
                            if domain:
                                buffer.add_log(f"Analysis task: Processing web content from {domain}", high_level=True)
                        
                        return content
                    else:
                        self.url_tracking['failed_scrapes'] += 1
                        if buffer:
                            buffer.add_log(f"Failed to scrape URL: {url}")
                        return None
                except Exception as e:
                    self.url_tracking['failed_scrapes'] += 1
                    if buffer:
                        buffer.add_log(f"Error scraping URL {url}: {str(e)}")
                    return None
            web_scraper.scrape_url = tracked_scrape_url
    
    def _classify_and_count_url(self, url, buffer=None):

        url_lower = url.lower()
        tracked = False
        if 'wikipedia.org' in url_lower:
            self.url_tracking['wikipedia_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"Wikipedia page processed: {url}", high_level=True)
        
        if any(news_domain in url_lower for news_domain in 
                ['news', 'cnbc', 'bbc', 'reuters', 'cnn', 'nytimes', 
                'washingtonpost', 'guardian', 'aljazeera', 'npr']):
            self.url_tracking['news_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"News source processed: {url}", high_level=True)
        
        if 'arxiv.org' in url_lower:
            self.url_tracking['arxiv_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"ArXiv paper processed: {url}", high_level=True)
        
        if any(stat_domain in url_lower for stat_domain in 
                ['statista', 'worldbank', 'data.gov', 'ourworldindata', 
                'census.gov', 'bls.gov', 'oecd.org']):
            self.url_tracking['stats_sources_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"Statistics source processed: {url}", high_level=True)
        
        if url_lower.endswith('.pdf'):
            self.url_tracking['academic_pdf_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"Academic PDF processed: {url}", high_level=True)
        
        if 'doi.org' in url_lower or '/doi/' in url_lower:
            self.url_tracking['doi_papers_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"DOI paper processed: {url}", high_level=True)
        
        if any(academic_domain in url_lower for academic_domain in 
                ['edu', 'ac.uk', 'researchgate', 'springer', 'sciencedirect', 
                'jstor', 'ieee', 'mdpi', 'ncbi', 'scielo', 'ssrn']):
            self.url_tracking['academic_pdf_count'] += 1
            tracked = True
            if buffer:
                buffer.add_log(f"Academic source processed: {url}", high_level=True)
        if not tracked:
            self.url_tracking['web_page_count'] += 1

