from typing import Dict, List, Any, Callable, Awaitable
from modules.utils.citation import SourceReference
import asyncio

class StatisticsResearcher:
    def __init__(self, process_query, search_client, web_scraper, article_storage, references, citation_manager):
        self.process_query = process_query
        self.search_client = search_client
        self.web_scraper = web_scraper
        self.article_storage = article_storage
        self.references = references
        self.citation_manager = citation_manager
        self.statistics_dorks = [
            'site:statista.com "{topic}" statistics',
            'site:ourworldindata.org "{topic}"',
            'site:data.gov "{topic}" statistics',
            'site:data.worldbank.org "{topic}" data',
            'site:bleepingcomputer.com "{topic}" statistics',
            'site:therecord.media "{topic}" data',
            'site:kaggle.com "{topic}" dataset',
            'site:bls.gov "{topic}" data',
            'site:oecd.org "{topic}" statistics',
            'site:census.gov "{topic}" statistics'
        ]
        
    async def research_statistics_sources(self, topic: str, buffer: Any, academic_sources: Dict) -> Dict:

        buffer.add_log(f"Researching statistics and data sources using Google Dorks for: {topic}", high_level=True)
        topic_words = topic.split()
        concise_topic = topic
        if len(topic_words) > 3:
            if len(topic_words) > 5:
                concise_topic = ' '.join(topic_words[:3])  # Take first 3 words
            else:
                concise_topic = ' '.join(topic_words[:2])  # Take first 2 words
                
        buffer.add_log(f"Using concise search term for statistics dorks: '{concise_topic}'", high_level=True)
        
        statistics_sources = []
        try:
            selected_dorks = self.statistics_dorks[:5]  # Limit to first 5 dorks for speed
            
            # Process in batches of 2 dorks at a time
            batch_size = 2
            for i in range(0, len(selected_dorks), batch_size):
                batch_dorks = selected_dorks[i:i+batch_size]
                tasks = []
                for dork in batch_dorks:
                    query = dork.format(topic=concise_topic)
                    tasks.append(self._process_statistics_dork(query, statistics_sources, topic, buffer))
                # Properly await all tasks in the batch
                await asyncio.gather(*tasks)
                
                # Check if we have enough sources
                if len(statistics_sources) >= 3:
                    buffer.add_log(f"Collected {len(statistics_sources)} statistics sources, stopping search for efficiency", high_level=True)
                    break
                    
            if len(statistics_sources) > 3:
                statistics_sources = statistics_sources[:3]
                
            for source in statistics_sources:
                if 'url' not in source and 'source' in source:
                    parts = source['source'].split(' - ', 1)
                    if len(parts) > 1:
                        source['url'] = parts[1]
                
            academic_sources["statistics_sources"] = statistics_sources
            buffer.add_log(f"Successfully collected {len(statistics_sources)} statistics sources", high_level=True)
            return {"statistics_sources": statistics_sources}
            
        except Exception as e:
            buffer.add_log(f"Error researching statistics sources: {str(e)}", high_level=True)
            return {"statistics_sources": []}
    
    async def _process_statistics_dork(self, query, statistics_sources, topic, buffer):

        buffer.add_log(f"Using Google Dork for statistics: {query}", high_level=True)
        
        search_results = await self.search_client.google_search(query, buffer)
        if not search_results:
            buffer.add_log(f"No search results for dork: {query}")
            return
            
        buffer.add_log(f"Found {len(search_results)} search results for dork: {query}")
        for result in search_results[:2]:
            try:
                url = result.get("link", "")
                if not url:
                    continue
                if any(source.get("source", "").endswith(url) for source in statistics_sources):
                    continue
                
                title = self._safe_get_title(result, topic, "Statistics on")
                if self.article_storage.has_article(url):
                    article_metadata = self.article_storage.get_article_by_url(url)
                    article_id = article_metadata["id"]
                    content = self.article_storage.get_article_content(article_id)
                    summary = article_metadata.get("metadata", {}).get("summary", "")
                    if not summary:  # Generate new summary if needed
                        summary = await self._summarize_content(content, "Statistics", topic, buffer)
                        self.article_storage.add_summary_to_article(article_id, summary)
                else:
                    buffer.add_log(f"Scraping statistics source: {url}", high_level=True)
                    content = await self.web_scraper.scrape_url(url, buffer)
                    if not content or len(content) < 300:  # Ensure we have meaningful content
                        continue
                    
                    article_id = self.article_storage.store_article(
                        url=url,
                        title=title,
                        content=content,
                        source_type="statistics",
                        metadata={
                            "topic": topic,
                            "query": query,
                            "snippet": result.get("snippet", "")
                        }
                    )
                    summary = await self._summarize_content(content, "Statistics", topic, buffer)
                    self.article_storage.add_summary_to_article(article_id, summary)
                source_ref = SourceReference(
                    title=title,
                    url=url,
                    source_type="statistics"
                )
                source_ref.relevance_score = 0.8  # Statistics sources are highly relevant
                source_ref.calculate_scores()
                self.references[url] = source_ref
                self.citation_manager.add_reference(source_ref)
                
                statistics_sources.append({
                    "source": f"{title} - {url}",
                    "content": content[:5000] if len(content) > 5000 else content,  # Truncate content for memory efficiency
                    "summary": summary,
                    "source_type": "statistics",
                    "article_id": article_id,
                    "title": title,
                    "url": url  # Explicitly include URL for tracking
                })
                if len(statistics_sources) >= 4:
                    break
                    
            except Exception as e:
                buffer.add_log(f"Error processing statistics source: {str(e)}")
                continue
            
    async def _summarize_content(self, content: str, source_type: str, topic: str, buffer: Any) -> str:

        max_content_length = 3000
        truncated_content = content[:max_content_length] + "..." if len(content) > max_content_length else content
        
        prompt = f"""
You are an academic research assistant with a natural writing style. Summarize the following {source_type} content about "{topic}".
Extract key information, statistics, methodologies, and findings that would be valuable for an academic paper.

Content:
{truncated_content}

Create a concise summary (200-300 words) that:
1. Identifies the main points relevant to {topic}
2. Extracts factual information and data
3. Notes any methodologies or approaches described
4. Highlights conclusions or insights
5. Maintains a scholarly but natural tone

Write like a thoughtful human researcher would, with varied sentence structure, 
natural transitions, and genuine intellectual engagement with the material.
Avoid formulaic expressions and overly mechanical language.

The summary should read as if written by a human academic, suitable for integration into a research paper.
"""
        
        try:
            summary = await self.process_query(prompt, buffer)
            if buffer.verbose:
                buffer.add_log(f"Generated summary of {len(summary)} chars for source")
            return summary
        except Exception as e:
            buffer.add_log(f"Error generating content summary: {str(e)}")
            return "Content processing failed. Please see original source."
            
    def _safe_get_title(self, obj, topic="research topic", default_prefix="Untitled Document on"):

        if not obj:
            return f"{default_prefix} {topic}"
        if isinstance(obj, dict):
            for key in ["title", "Title", "name", "Name"]:
                if key in obj and obj[key]:
                    return str(obj[key])
            if "source" in obj and obj["source"]:
                parts = str(obj["source"]).split(" - ")
                if len(parts) > 0 and parts[0].strip():
                    return parts[0].strip()
        try:
            if hasattr(obj, "title") and getattr(obj, "title"):
                return str(getattr(obj, "title"))
        except:
            pass
        return f"{default_prefix} {topic}"

