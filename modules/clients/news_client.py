from GoogleNews import GoogleNews
from typing import List, Dict, Optional, Any, Union
import asyncio
import datetime
import re
import json
import logging
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.rate_limiter import RateLimitHandler
from modules.utils.citation import SourceReference
from playwright.async_api import async_playwright

class NewsClient:
    COUNTRY_TO_REGION = {
        'united states': 'US', 'us': 'US', 'usa': 'US', 'america': 'US',
        'united kingdom': 'GB', 'uk': 'GB', 'england': 'GB', 'britain': 'GB',
        'australia': 'AU', 'canada': 'CA', 'india': 'IN', 'france': 'FR',
        'germany': 'DE', 'italy': 'IT', 'spain': 'ES', 'japan': 'JP',
        'china': 'CN', 'russia': 'RU', 'brazil': 'BR', 'mexico': 'MX',
        'south africa': 'ZA', 'nigeria': 'NG', 'egypt': 'EG',
        'saudi arabia': 'SA', 'uae': 'AE', 'united arab emirates': 'AE',
        'pakistan': 'PK', 'bangladesh': 'BD', 'indonesia': 'ID',
        'thailand': 'TH', 'vietnam': 'VN', 'philippines': 'PH',
        'south korea': 'KR', 'korea': 'KR', 'turkey': 'TR',
        'sweden': 'SE', 'norway': 'NO', 'denmark': 'DK',
        'finland': 'FI', 'netherlands': 'NL', 'belgium': 'BE',
        'switzerland': 'CH', 'austria': 'AT', 'portugal': 'PT',
        'greece': 'GR', 'poland': 'PL', 'ireland': 'IE',
        'new zealand': 'NZ', 'argentina': 'AR', 'chile': 'CL',
        'colombia': 'CO', 'peru': 'PE', 'venezuela': 'VE',
        'singapore': 'SG', 'malaysia': 'MY', 'israel': 'IL'
    }

    def __init__(self, rate_limiter: RateLimitHandler):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger("NewsClient")
    
    def _detect_region_from_topic(self, topic: str) -> str:

        topic_lower = topic.lower()
        for country, region_code in self.COUNTRY_TO_REGION.items():
            if country.lower() in topic_lower:
                return region_code
        return 'US'
    
    async def get_news_links(self, query: str, buffer: AsyncBuffer, pages: int = 2, region: str = None) -> List[Dict]:

        buffer.add_log(f"Searching news for: {query}", high_level=True)
        
        try:
            await self.rate_limiter.wait_if_needed("news")
            if not region:
                region = self._detect_region_from_topic(query)
                buffer.add_log(f"Using region '{region}' for news search", high_level=True)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, lambda: self._sync_get_news(query, pages, region)
            )
            
            if not results:
                buffer.add_log("No news results found")
                return []
                
            buffer.add_log(f"Found {len(results)} news articles related to '{query}'")
            return results
            
        except Exception as e:
            buffer.add_log(f"Error fetching news: {str(e)}")
            return []
    
    def _sync_get_news(self, query: str, pages: int = 2, region: str = 'US') -> List[Dict]:

        googlenews = GoogleNews(lang='en', region=region)
        googlenews.search(query)
        
        all_results = []
        
        for i in range(1, pages+1):
            if i > 1:
                googlenews.getpage(i)
            
            results = googlenews.result()
            for item in results:
                if 'link' in item and item['link'] not in [r.get('link') for r in all_results]:
                    item_dict = {
                        'title': item.get('title', ''),
                        'link': item.get('link', ''),
                        'media': item.get('media', ''),
                        'desc': item.get('desc', ''),
                        'source_type': 'news'
                    }
                    if 'date' in item:
                        if isinstance(item['date'], datetime.datetime):
                            item_dict['date'] = item['date'].isoformat()
                        else:
                            item_dict['date'] = str(item['date'])
                    else:
                        item_dict['date'] = ''
                        
                    if 'datetime' in item:
                        if isinstance(item['datetime'], datetime.datetime):
                            item_dict['datetime'] = item['datetime'].isoformat()
                        else:
                            item_dict['datetime'] = str(item['datetime'])
                    else:
                        item_dict['datetime'] = ''
                    
                    all_results.append(item_dict)
        
        return all_results
        
    async def generate_news_queries(self, topic: str, buffer: AsyncBuffer, process_query_func) -> List[str]:

        prompt = f"""
I need to research news articles about: "{topic}"

Generate 5-8 specific search queries that would provide comprehensive coverage from news sources. These queries should:
1. Cover different aspects or angles of the topic
2. Be specific enough to find relevant news articles
3. Include relevant timeline context (recent developments, historical background, etc.)
4. Be suitable for news search engines

If the topic involves a specific country, region, or location, make sure to highlight that in some queries.

Format your response as a JSON array of strings with the search queries.
Example: ["Brexit economic impact UK businesses", "Brexit Northern Ireland protocol latest developments", "Brexit EU trade relations 2023"]

Only return the JSON array, nothing else.
"""
        try:
            response = await process_query_func(prompt, buffer)
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].strip()
            queries = json.loads(json_str)
            buffer.add_log(f"Generated {len(queries)} optimized news search queries", high_level=True)
            return queries
        except Exception as e:
            buffer.add_log(f"Error generating news queries: {str(e)}", high_level=True)
            return [
                f"{topic} latest news", 
                f"{topic} recent developments", 
                f"{topic} analysis", 
                f"{topic} impact", 
                f"{topic} background"
            ]

    async def generate_title(self, topic: str, buffer: AsyncBuffer, process_query_func) -> str:

        prompt = f"""
Generate a compelling, academic title for a research paper analyzing recent news and developments about:
"{topic}"

The title should be:
1. Clear and informative
2. Professional and academic in tone
3. Engaging to readers
4. 10-15 words in length
5. Include relevant keywords

Only return the title itself, no additional text or explanation.
"""
        try:
            title = await process_query_func(prompt, buffer)
            title = title.strip().strip('"').strip("'")
            buffer.add_log(f"Generated research paper title: {title}", high_level=True)
            return title
        except Exception as e:
            buffer.add_log(f"Error generating title: {str(e)}", high_level=True)
            return f"Recent Developments and Analysis: A Comprehensive Study of {topic}"

    async def detect_event_topic(self, topic: str, buffer: AsyncBuffer, process_query_func) -> Dict:

        buffer.add_log(f"Analyzing if '{topic}' is an event-based or concept-based topic", high_level=True)
        
        try:
            event_keywords = ["disaster", "election", "pandemic", "outbreak", "crisis", "attack", "war", 
                             "conflict", "scandal", "tragedy", "protest", "rally", "coup", "invasion",
                             "assassination", "bombing", "shooting", "earthquake", "hurricane", "flood"]
            is_likely_event = any(keyword in topic.lower() for keyword in event_keywords)
            date_patterns = [
                r'\b\d{4}\b',            # Year (e.g., 2023)
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # Date formats like 11/23/2023
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',  # Month names
                r'\b(jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b'  # Abbreviated months
            ]
            
            has_date = any(re.search(pattern, topic.lower()) for pattern in date_patterns)
            try:
                title = await self.generate_title(topic, buffer, process_query_func)
            except Exception as e:
                buffer.add_log(f"Error generating title: {str(e)}", high_level=True)
                title = f"Comprehensive Analysis of {topic}"
            if is_likely_event or has_date:
                gemini_prompt = f"""
Analyze this topic: "{topic}"

Determine if this topic refers to:
1. A specific real-world event (like a disaster, conflict, election, etc.)
2. A general concept, technology, or field of study

Also identify:
- 3-5 key components or aspects that make up this topic
- Any specific countries or regions this topic is primarily associated with
- Time sensitivity (is this a current event, historical event, ongoing situation, or timeless concept?)

Provide your response as valid JSON with the following structure:
{{
  "is_event": true/false,
  "reasoning": "brief explanation of your reasoning",
  "key_components": ["component1", "component2", "component3"],
  "regions": ["Country1", "Region1"] or [],
  "time_sensitivity": "current/historical/ongoing/timeless",
  "search_components": ["search query 1", "search query 2", "search query 3", "search query 4"]
}}

Return ONLY the JSON object, nothing else.
"""
                
                try:
                    gemini_response = await process_query_func(gemini_prompt, buffer)
                    json_match = re.search(r'```(?:json)?\s*(.*?)```', gemini_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = gemini_response
                    try:
                        analysis = json.loads(json_str)
                    except json.JSONDecodeError as json_err:
                        buffer.add_log(f"Error decoding JSON from Gemini response: {str(json_err)}", high_level=True)
                        analysis = {
                            "is_event": is_likely_event,  # Use our keyword detection as fallback
                            "reasoning": "Fallback due to JSON parsing error",
                            "key_components": [topic],
                            "regions": [],
                            "time_sensitivity": "unknown",
                            "search_components": [f"{topic} overview", f"{topic} analysis"]
                        }
                    
                    is_event = analysis.get("is_event", False)
                    key_components = analysis.get("key_components", [])
                    regions = analysis.get("regions", [])
                    search_components = analysis.get("search_components", [])
                    region_code = 'US'  # Default
                    if regions:
                        for region in regions:
                            detected_code = self._detect_region_from_topic(region)
                            if detected_code != 'US':  # If we found a specific region
                                region_code = detected_code
                                break
                    
                    if is_event:
                        buffer.add_log(f"'{topic}' confirmed as a real-world event - will include news sources from region {region_code}", high_level=True)
                        try:
                            news_queries = await self.generate_news_queries(topic, buffer, process_query_func)
                        except Exception as query_err:
                            buffer.add_log(f"Error generating news queries: {str(query_err)}", high_level=True)
                            news_queries = [f"{topic} latest news", f"{topic} current developments", f"{topic} update"]
                        all_news = []
                        for query in news_queries[:2]:
                            try:
                                news_results = await self.get_news_links(query, buffer, pages=1, region=region_code)
                                for result in news_results:
                                    if result['link'] not in [r.get('link', '') for r in all_news]:
                                        all_news.append(result)
                            except Exception as news_err:
                                buffer.add_log(f"Error fetching news for query '{query}': {str(news_err)}", high_level=True)
                                continue
                        
                        return {
                            "is_event": True,
                            "title": title,
                            "news_articles": all_news[:8],  # Limit to top 8 articles for focus
                            "event_queries": news_queries + search_components,
                            "key_components": key_components,
                            "regions": regions,
                            "region_code": region_code,
                            "reasoning": analysis.get("reasoning", ""),
                            "time_sensitivity": analysis.get("time_sensitivity", "current")
                        }
                    else:
                        buffer.add_log(f"'{topic}' analyzed as a concept rather than a specific event", high_level=True)
                        
                        return {
                            "is_event": False,
                            "title": title,
                            "news_articles": [],  # No news articles for concepts
                            "concept_queries": search_components if search_components else [
                                f"{topic} definition", 
                                f"{topic} overview", 
                                f"{topic} applications",
                                f"{topic} examples"
                            ],
                            "key_components": key_components,
                            "regions": regions,
                            "region_code": region_code,
                            "reasoning": analysis.get("reasoning", ""),
                            "time_sensitivity": analysis.get("time_sensitivity", "timeless")
                        }
                    
                except Exception as e:
                    buffer.add_log(f"Error in Gemini event detection: {str(e)} - falling back to keyword-based detection", high_level=True)
                    return self._create_fallback_event_analysis(topic, is_likely_event, title, buffer)
            else:
                buffer.add_log(f"'{topic}' appears to be concept-based, skipping detailed event analysis", high_level=True)
                return {
                    "is_event": False,
                    "title": title,
                    "news_articles": [],  # No news articles for concepts
                    "concept_queries": [
                        f"{topic} definition",
                        f"{topic} overview", 
                        f"{topic} techniques",
                        f"{topic} applications",
                        f"{topic} examples",
                        f"{topic} current research"
                    ],
                    "key_components": [topic],
                    "regions": [],
                    "region_code": "US",
                    "reasoning": "Topic is a concept rather than an event",
                    "time_sensitivity": "timeless"
                }
        except Exception as e:
            buffer.add_log(f"Critical error in event topic detection: {str(e)}", high_level=True)
            return {
                "is_event": False,
                "title": f"Analysis of {topic}",
                "news_articles": [],
                "concept_queries": [f"{topic} overview", f"{topic} definition", f"{topic} applications"],
                "key_components": [topic],
                "regions": [],
                "region_code": "US",
                "reasoning": "Fallback due to critical error in detection",
                "time_sensitivity": "unknown"
            }

    def _create_fallback_event_analysis(self, topic: str, is_likely_event: bool, title: str, buffer: AsyncBuffer) -> Dict:

        buffer.add_log(f"Creating fallback event analysis for: {topic}", high_level=True)
        region_code = self._detect_region_from_topic(topic)
        
        if is_likely_event:
            return {
                "is_event": True,
                "title": title or f"Analysis of {topic} Event",
                "news_articles": [],  # Empty as we couldn't fetch any
                "event_queries": [
                    f"{topic} latest news",
                    f"{topic} recent developments",
                    f"{topic} analysis",
                    f"{topic} timeline",
                    f"{topic} background",
                    f"{topic} impact"
                ],
                "key_components": [topic],
                "regions": [],
                "region_code": region_code,
                "reasoning": "Fallback detection based on keywords",
                "time_sensitivity": "current"
            }
        else:
            return {
                "is_event": False,
                "title": title or f"Analysis of {topic} Concept",
                "news_articles": [],
                "concept_queries": [
                    f"{topic} definition",
                    f"{topic} overview",
                    f"{topic} applications",
                    f"{topic} examples",
                    f"{topic} techniques",
                    f"{topic} history"
                ],
                "key_components": [topic],
                "regions": [],
                "region_code": region_code,
                "reasoning": "Fallback detection as concept",
                "time_sensitivity": "timeless"
            }
