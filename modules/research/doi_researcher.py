import json
import asyncio
from typing import Dict, List, Any, Callable, Awaitable
from modules.utils.citation import SourceReference

class DOIResearcher:
    def __init__(self, process_query, web_scraper, article_storage, references, citation_manager, url_tracking):
        self.process_query = process_query
        self.web_scraper = web_scraper
        self.article_storage = article_storage
        self.references = references
        self.citation_manager = citation_manager
        self.url_tracking = url_tracking
        
    async def research_doi_papers(self, topic: str, buffer: Any, academic_sources: Dict) -> Dict:

        buffer.add_log(f"Researching papers with DOIs for: {topic}", high_level=True)
        
        doi_papers = []
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            sanitized_topic = ''.join(c for c in topic if c.isalnum() or c.isspace())
            try:
                from modules.clients.academic_search import search_paper1, SciHubLink
                search_results_raw = await loop.run_in_executor(None, lambda: search_paper1(sanitized_topic))
            except Exception as e:
                buffer.add_log(f"Error calling search_paper1: {str(e)}", high_level=True)
                search_results_raw = "[]"  # Default to empty list
            try:
                import json
                search_results = json.loads(search_results_raw)
                if not isinstance(search_results, list):
                    search_results = [search_results] if search_results else []
                valid_results = []
                for result in search_results:
                    if isinstance(result, dict) and any(key in result for key in ["title", "Title", "url", "Read Link"]):
                        valid_results.append(result)
                    
                search_results = valid_results
            except json.JSONDecodeError as e:
                buffer.add_log(f"Error decoding JSON from search_paper1 results: {str(e)}", high_level=True)
                search_results = []
                
            if not search_results:
                buffer.add_log(f"No search results for DOI papers: {topic}")
                return {"doi_papers": []}
            
            buffer.add_log(f"Found {len(search_results)} search results for DOI papers: {topic}")
            tasks = []
            for i, result in enumerate(search_results[:3]):  # Process top 3 results
                tasks.append(self._process_doi_paper(result, topic, buffer))
            paper_results = await asyncio.gather(*tasks)
            doi_papers = [paper for paper in paper_results if paper is not None]
            self.url_tracking['doi_papers_count'] += len(doi_papers)
            
            academic_sources["doi_papers"] = doi_papers
            buffer.add_log(f"Successfully processed {len(doi_papers)} DOI papers out of {len(search_results[:3])} attempts", high_level=True)
            
            return {"doi_papers": doi_papers}
            
        except Exception as e:
            buffer.add_log(f"Error researching DOI papers: {str(e)}", high_level=True)
            return {"doi_papers": []}
    
    async def _process_doi_paper(self, result, topic, buffer):

        try:
            url = result.get("Read Link") or result.get("url", "")
            title = self._safe_get_title(result, topic, "Paper on")
            doi = result.get("DOI") or result.get("doi", "")
            authors = result.get("Authors") or result.get("authors", [])
            if isinstance(authors, str):
                authors = [authors]
            elif not authors:
                authors = ["Unknown Author"]
                
            published = result.get("Publication Date") or result.get("published", "")
            
            if not url or url == "No Link":
                buffer.add_log(f"No valid URL for paper: {title}")
                return None
            if not (url.startswith("http://") or url.startswith("https://")):
                if doi:
                    url = f"https://doi.org/{doi}"
                else:
                    buffer.add_log(f"Invalid URL format and no DOI for paper: {title}")
                    return None
            if self.article_storage.has_article(url):
                buffer.add_log(f"Using previously stored paper: {title}")
                article_metadata = self.article_storage.get_article_by_url(url)
                article_id = article_metadata["id"]
                content = self.article_storage.get_article_content(article_id)
                summary = article_metadata.get("metadata", {}).get("summary", "")
                if not summary:  # Generate new summary if needed
                    summary = await self._summarize_content(content, "DOI Paper", topic, buffer)
                    self.article_storage.add_summary_to_article(article_id, summary)
            else:
                buffer.add_log(f"Downloading paper: {url}", high_level=True)
                content = await self.web_scraper.scrape_url(url, buffer)
                if not content:
                    if doi:
                        buffer.add_log(f"Trying SciHub for DOI: {doi}", high_level=True)
                        try:
                            from modules.clients.academic_search import SciHubLink
                            loop = asyncio.get_event_loop()
                            sci_hub_result_raw = await loop.run_in_executor(None, lambda: SciHubLink(doi))
                            sci_hub_result = json.loads(sci_hub_result_raw)
                            pdf_link = sci_hub_result.get("pdf_link")
                            
                            if pdf_link:
                                buffer.add_log(f"Found PDF link via SciHub: {pdf_link}", high_level=True)
                                content = await self.web_scraper.scrape_url(pdf_link, buffer)
                        except Exception as e:
                            buffer.add_log(f"Error using SciHub: {str(e)}", high_level=True)
                    
                    if not content:
                        buffer.add_log(f"Failed to get content for: {url}", high_level=True)
                        return None
                
                article_id = self.article_storage.store_article(
                    url=url,
                    title=title,
                    content=content,
                    source_type="doi_paper",
                    metadata={
                        "topic": topic,
                        "doi": doi,
                        "authors": authors,
                        "published": published
                    }
                )
                summary = await self._summarize_content(content, "DOI Paper", topic, buffer)
                self.article_storage.add_summary_to_article(article_id, summary)
            source_ref = SourceReference(
                title=title,
                url=url,
                source_type="doi_paper",
                authors=authors if isinstance(authors, list) else [authors],
                publication_date=published
            )
            source_ref.relevance_score = 0.9  # DOI papers are highly relevant
            source_ref.calculate_scores()
            self.references[url] = source_ref
            self.citation_manager.add_reference(source_ref)
            
            return {
                "source": f"{title} - {url}",
                "content": content[:5000] if len(content) > 5000 else content,  # Truncate content for memory efficiency
                "summary": summary,
                "source_type": "doi_paper",
                "article_id": article_id,
                "title": title,  # Explicitly add title to ensure it's available
                "url": url,      # Explicitly include URL for tracking
                "doi": doi      # Include DOI for better citation
            }
        
        except Exception as e:
            buffer.add_log(f"Error processing DOI paper: {str(e)}")
            return None
            
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

