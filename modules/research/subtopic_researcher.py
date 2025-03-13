from typing import Dict, List, Any, Callable, Awaitable
from modules.utils.citation import SourceReference

class SubtopicResearcher:
    def __init__(self, process_query, web_scraper, wikipedia_client, search_client, 
                article_storage, references, citation_manager, url_tracking):
        self.process_query = process_query
        self.web_scraper = web_scraper
        self.wikipedia_client = wikipedia_client
        self.search_client = search_client
        self.article_storage = article_storage
        self.references = references
        self.citation_manager = citation_manager
        self.url_tracking = url_tracking
        self.visualizer = None  # This will be set by the main class
        
    async def research_subtopic(self, topic: str, subtopic_data: Dict, buffer: Any, combined_insights: Dict, progress: Dict) -> Dict:

        buffer.add_log(f"Researching subtopic: {subtopic_data['subtopic'] if isinstance(subtopic_data, dict) and 'subtopic' in subtopic_data else 'Unknown subtopic'}", high_level=True)
        
        try:
            if not isinstance(subtopic_data, dict):
                buffer.add_log("Invalid subtopic data format, using fallback structure", high_level=True)
                subtopic_data = {
                    "subtopic": str(subtopic_data) if subtopic_data else f"Aspect of {topic}",
                    "search_queries": [f"{topic} overview"]
                }
            subtopic = subtopic_data.get("subtopic", f"Aspect of {topic}")
            search_queries = subtopic_data.get("search_queries", [])
            if not isinstance(search_queries, list) or not search_queries:
                search_queries = [f"{topic} {subtopic}"]
            initial_web_count = self.url_tracking['web_page_count']
            research_materials = []
            is_event_topic = False  # This would come from research_data in the original code
            buffer.add_log(f"Searching for academic sources first for subtopic: {subtopic}", high_level=True)
            relevant_doi_papers = []
            for doi_paper in combined_insights.get("doi_papers", []):
                paper_content = doi_paper.get("content", "")
                if not paper_content:
                    continue
                subtopic_keywords = subtopic.lower().split()
                if any(keyword in paper_content.lower() for keyword in subtopic_keywords):
                    relevant_doi_papers.append(doi_paper)
                    
            if relevant_doi_papers:
                buffer.add_log(f"Found {len(relevant_doi_papers)} relevant DOI papers for subtopic: {subtopic}", high_level=True)
                research_materials.extend(relevant_doi_papers)
            relevant_arxiv_papers = []
            for i, paper in enumerate(combined_insights.get("arxiv_papers", [])):
                if isinstance(paper, dict) and "summary" in paper:
                    paper_summary = paper["summary"]
                    subtopic_keywords = subtopic.lower().split()
                    if any(keyword in paper_summary.lower() for keyword in subtopic_keywords):
                        article_id = combined_insights.get("article_ids", [])[i] if i < len(combined_insights.get("article_ids", [])) else None
                        if article_id:
                            content = self.article_storage.get_article_content(article_id) or ""
                            relevant_arxiv_papers.append({
                                "source": f"{paper['title']} - {paper.get('pdf_url', 'arXiv')}",
                                "content": content,
                                "summary": paper_summary,
                                "source_type": "arxiv",
                                "article_id": article_id
                            })
                        
            if relevant_arxiv_papers:
                buffer.add_log(f"Found {len(relevant_arxiv_papers)} relevant arXiv papers for subtopic: {subtopic}", high_level=True)
                research_materials.extend(relevant_arxiv_papers)
            if len(relevant_doi_papers) + len(relevant_arxiv_papers) < 2:
                try:
                    search_query = f"{topic} {subtopic}"
                    buffer.add_log(f"Searching for additional academic papers for: {search_query}", high_level=True)
                    academic_dorks = [
                        'site:*.edu filetype:pdf "{topic}"',
                        'site:*.gov filetype:pdf "{topic}"',
                        'site:*.ac filetype:pdf "{topic}"'
                    ]
                    
                    for dork in academic_dorks[:3]:  # Use just a few to save time
                        query = dork.format(topic=search_query)
                        search_results = await self.search_client.google_search(query, buffer)
                        if search_results:
                            for result in search_results[:2]:  # Process top 2 results
                                url = result.get("link")
                                if not url or not url.startswith(("http://", "https://")):
                                    continue
                                if url.lower().endswith('.pdf') or any(academic_domain in url.lower() for academic_domain in 
                                                                      ['edu', 'ac.uk', 'researchgate', 'springer', 
                                                                       'sciencedirect', 'jstor', 'ieee', 'mdpi', 
                                                                       'ncbi', 'scielo', 'ssrn']):
                                    if self.article_storage.has_article(url):
                                        buffer.add_log(f"Using previously stored academic source: {result.get('title')}")
                                        article_metadata = self.article_storage.get_article_by_url(url)
                                        article_id = article_metadata["id"]
                                        content = self.article_storage.get_article_content(article_id)
                                        summary = article_metadata.get("metadata", {}).get("summary")
                                        if not summary:
                                            summary = await self._summarize_content(content, "Academic", subtopic, buffer)
                                            self.article_storage.add_summary_to_article(article_id, summary)
                                    else:
                                        buffer.add_log(f"Scraping new academic source: {url}", high_level=True)
                                        content = await self.web_scraper.scrape_url(url, buffer)
                                        if not content:
                                            continue
                                            
                                        article_id = self.article_storage.store_article(
                                            url=url,
                                            title=result.get("title", "Untitled"),
                                            content=content,
                                            source_type="academic",
                                            metadata={
                                                "topic": topic,
                                                "subtopic": subtopic,
                                                "query": query,
                                                "snippet": result.get("snippet", "")
                                            }
                                        )
                                        summary = await self._summarize_content(content, "Academic", subtopic, buffer)
                                        self.article_storage.add_summary_to_article(article_id, summary)
                                    source_ref = SourceReference(
                                        title=result.get("title", "Untitled"),
                                        url=url,
                                        source_type="academic"
                                    )
                                    source_ref.relevance_score = 0.85  # Academic sources are highly relevant
                                    source_ref.calculate_scores()
                                    self.references[url] = source_ref
                                    self.citation_manager.add_reference(source_ref)
                                    
                                    research_materials.append({
                                        "source": f"{result.get('title')} - {url}",
                                        "content": content,
                                        "summary": summary,
                                        "source_type": "academic",
                                        "article_id": article_id
                                    })
                except Exception as e:
                    buffer.add_log(f"Error searching for additional academic papers: {str(e)}", high_level=True)
            buffer.add_log("Searching Wikipedia for background information", high_level=True)
            wiki_content = await self.wikipedia_client.fetch_wikipedia_content(subtopic, buffer, self.references)
            if wiki_content:
                wiki_url = f"wikipedia:{subtopic}"  # Use pseudo-URL for Wikipedia
                if not self.article_storage.has_article(wiki_url):
                    article_id = self.article_storage.store_article(
                        url=wiki_url,
                        title=f"Wikipedia - {subtopic}",
                        content=wiki_content,
                        source_type="wikipedia",
                        metadata={"topic": topic, "subtopic": subtopic}
                    )
                    buffer.add_log(f"Stored Wikipedia article with ID: {article_id}")
                else:
                    buffer.add_log(f"Using previously stored Wikipedia article for {subtopic}")
                    article_metadata = self.article_storage.get_article_by_url(wiki_url)
                    article_id = article_metadata["id"]
                    wiki_content = self.article_storage.get_article_content(article_id) or wiki_content
                wiki_summary = await self._summarize_content(wiki_content, "Wikipedia", subtopic, buffer)
                self.article_storage.add_summary_to_article(article_id, wiki_summary)
                
                research_materials.append({
                    "source": f"Wikipedia - {subtopic}",
                    "content": wiki_content,
                    "summary": wiki_summary,
                    "source_type": "wikipedia",
                    "article_id": article_id
                })
            if is_event_topic:
                buffer.add_log("Including news sources for event-based topic", high_level=True)
                news_articles = []  # This would come from research_data in the original code
                
                relevant_news = []
                subtopic_keywords = subtopic.lower().split()
                for article in news_articles:
                    if any(keyword in article['title'].lower() or keyword in article.get('desc', '').lower() 
                           for keyword in subtopic_keywords):
                        relevant_news.append(article)
                for i, article in enumerate(relevant_news[:3]):
                    url = article.get("link")
                    if not url or not url.startswith(("http://", "https://")):
                        continue
                    if self.article_storage.has_article(url):
                        buffer.add_log(f"Using previously stored news article: {article.get('title')}")
                        article_metadata = self.article_storage.get_article_by_url(url)
                        article_id = article_metadata["id"]
                        content = self.article_storage.get_article_content(article_id)
                        summary = article_metadata.get("metadata", {}).get("summary")
                        if not summary:  # Generate new summary if needed
                            summary = await self._summarize_content(content, "News", subtopic, buffer)
                            self.article_storage.add_summary_to_article(article_id, summary)
                    else:
                        content = await self.web_scraper.scrape_url(url, buffer)
                        if not content:
                            continue
                            
                        article_id = self.article_storage.store_article(
                            url=url,
                            title=article.get('title', 'Untitled'),
                            content=content,
                            source_type="news",
                            metadata={
                                "topic": topic,
                                "subtopic": subtopic,
                                "publication_date": article.get('date', ''),
                                "source": article.get('media', '')
                            }
                        )
                        summary = await self._summarize_content(content, "News", subtopic, buffer)
                        self.article_storage.add_summary_to_article(article_id, summary)
                    buffer.add_log(f"News source added: {url}")
                    source_ref = SourceReference(
                        title=article.get('title', 'Untitled'),
                        url=url,
                        source_type="news",
                        publication_date=article.get('date', ''),
                        authors=[article.get('media', 'Unknown')]
                    )
                    source_ref.relevance_score = 0.85  # News about current events is highly relevant
                    source_ref.calculate_scores()
                    self.references[url] = source_ref
                    self.citation_manager.add_reference(source_ref)
                    
                    research_materials.append({
                        "source": f"{article.get('title')} - {url}",
                        "content": content,
                        "summary": summary,
                        "source_type": "news",
                        "article_id": article_id
                    })
            else:
                buffer.add_log("Skipping news sources for non-event topic", high_level=True)
            for i, query in enumerate(search_queries):
                if len(research_materials) >= 12:
                    buffer.add_log("Collected sufficient research materials, skipping remaining queries", high_level=True)
                    break
                if len(query.split()) > 5:
                    query_parts = query.split()
                    query = ' '.join(query_parts[:4])  # Take first 4 words
                context_enhanced_query = self._enhance_search_query(query, subtopic, topic)
                buffer.add_log(f"Processing optimized search query: {context_enhanced_query}")
                if i == 0 or len(research_materials) < 3:  # Use more expensive research_google_search sparingly
                    search_results = await self.search_client.google_search(context_enhanced_query, buffer)
                else:
                    search_results = await self.search_client.combined_search(context_enhanced_query, buffer)
                    
                if not search_results:
                    buffer.add_log(f"No search results for query: {context_enhanced_query}")
                    continue
                    
                buffer.add_log(f"Found {len(search_results)} search results for query: {context_enhanced_query}")
                for i, result in enumerate(search_results[:3]):
                    url = result.get("link")
                    if not url or not url.startswith(("http://", "https://")):
                        continue
                    if self.article_storage.has_article(url):
                        buffer.add_log(f"Using previously stored article: {result.get('title')}")
                        article_metadata = self.article_storage.get_article_by_url(url)
                        article_id = article_metadata["id"]
                        content = self.article_storage.get_article_content(article_id)
                        summary = article_metadata.get("metadata", {}).get("summary")
                        if not summary:  # Generate new summary if needed
                            summary = await self._summarize_content(content, "Web", subtopic, buffer)
                            self.article_storage.add_summary_to_article(article_id, summary)
                    else:
                        buffer.add_log(f"Scraping web page: {url}", high_level=True)
                        content = await self.web_scraper.scrape_url(url, buffer)
                        if not content:
                            continue
                        buffer.add_log(f"Web page scraped successfully (Total: {self.url_tracking['web_page_count']})", high_level=True)
                        progress["analyzing_count"] += 1
                        buffer.add_log(f"Analyzing content: #{progress['analyzing_count']} - {result.get('title', 'Untitled')}", high_level=True)
                            
                        article_id = self.article_storage.store_article(
                            url=url,
                            title=result.get("title", "Untitled"),
                            content=content,
                            source_type="web",
                            metadata={
                                "topic": topic,
                                "subtopic": subtopic,
                                "query": context_enhanced_query,
                                "snippet": result.get("snippet", "")
                            }
                        )
                        summary = await self._summarize_content(content, "Web", subtopic, buffer)
                        self.article_storage.add_summary_to_article(article_id, summary)
                    source_ref = SourceReference(
                        title=result.get("title", "Untitled"),
                        url=url,
                        source_type="web"
                    )
                    source_ref.relevance_score = 0.7  # Default relevance score
                    source_ref.calculate_scores()
                    self.references[url] = source_ref
                    self.citation_manager.add_reference(source_ref)
                    
                    research_materials.append({
                        "source": f"{result.get('title')} - {url}",
                        "content": content,
                        "summary": summary,
                        "source_type": "web",
                        "article_id": article_id
                    })
            web_pages_added = self.url_tracking['web_page_count'] - initial_web_count
            buffer.add_log(f"Added {web_pages_added} new web sources while researching '{subtopic}'", high_level=True)
            if not research_materials:
                buffer.add_log(f"No research materials found for subtopic: {subtopic}", high_level=True)
                section_content = f"No detailed information could be found for {subtopic}."
                sources = []
            else:
                combined_research = ""
                sources = []
                
                for i, material in enumerate(research_materials):
                    if not material.get("source"):
                        source_type = material.get("source_type", "web")
                        title = self._safe_get_title(material, subtopic, "Source on")
                        url = material.get("url", f"local-{i}")
                        material["source"] = f"{title} - {url}"
                        material["title"] = title  # Explicitly add title
                    source = material.get("source", f"Source {i+1}")
                    sources.append(source)
                    source_info = f"Source {i+1}: {source}"
                    summary_text = material.get('summary', 'No summary available')
                    combined_research += f"\n\n{source_info}\n{summary_text}"
                section_content = await self.generate_section_content(topic, subtopic, combined_research, buffer)
            try:
                image_path = await self.visualizer.generate_image_for_topic(subtopic, buffer, self.process_query)
            except Exception as e:
                buffer.add_log(f"Error generating image for subtopic: {str(e)}", high_level=True)
                image_path = None
            return {
                "subtopic": subtopic,
                "content": section_content,
                "sources": sources,
                "image_path": image_path,
                "research_materials": research_materials,  # Include the full research materials for reference
                "article_ids": [material.get("article_id") for material in research_materials if "article_id" in material],
                "web_pages_added": self.url_tracking['web_page_count'] - initial_web_count,
                "url_tracking": self.url_tracking  # Include current URL tracking stats
            }
            
        except Exception as e:
            buffer.add_log(f"Error researching subtopic: {str(e)}", high_level=True)
            default_subtopic = "Unknown subtopic" 
            if isinstance(subtopic_data, dict) and "subtopic" in subtopic_data:
                default_subtopic = subtopic_data["subtopic"]
                
            return {
                "subtopic": default_subtopic,
                "content": f"Research on {default_subtopic} could not be completed due to technical difficulties.",
                "sources": [],
                "image_path": None,
                "research_materials": [],
                "article_ids": [],
                "web_pages_added": 0,
                "url_tracking": self.url_tracking
            }
            
    async def generate_section_content(self, topic: str, subtopic: str, research_material: str, buffer: Any) -> str:
        prompt = f"""
You are writing a section of a professional research paper on "{topic}" - specifically the section about "{subtopic}".
Use the following research material (which contains summaries of multiple sources) to write a comprehensive, 
academically rigorous section (800-1200 words):

{research_material}

Write in a natural, engaging academic style with proper citations indicated as [1], [2], etc. where each number corresponds to the sources in the research material.
Important guidelines to follow:
- Use varied sentence structure and lengths - mix shorter sentences with longer, more complex ones
- Include occasional rhetorical questions to engage readers
- Use transitional phrases naturally (e.g., "However", "Moreover", "Interestingly")
- Incorporate thoughtful observations and analytical insights that feel like they come from a human researcher
- Avoid formulaic paragraph structures and repetitive sentence patterns
- Include occasional colloquial but academically appropriate phrases
- Maintain an authentic academic voice without sounding overly formal or robotic
- Make appropriate use of first-person plural when discussing implications (e.g., "We can observe that...")
- Include some nuanced points that show critical thinking, not just summarization
- Identify gaps or contradictions in the research naturally, as a human researcher would
- Use proper technical language and domain-specific terminology appropriately

Ensure the writing sounds like it was written by a thoughtful human academic rather than AI - with natural flow, 
varied expressions, and thoughtful analysis.

This is for an academic audience, so maintain appropriate scholarly tone while ensuring the text feels natural and engaging.
"""

        buffer.add_log(f"Generating content for section: {subtopic}", high_level=True)
        response = await self.process_query(prompt, buffer)
        buffer.add_log(f"Successfully generated content for section: {subtopic}", high_level=True)
        extracted_citations = self.citation_manager.extract_citations_from_text(response)
        buffer.add_log(f"Found {len(extracted_citations)} citations in the generated content")
        
        return response
        
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
            
    def _enhance_search_query(self, query: str, subtopic: str, main_topic: str) -> str:

        if main_topic.lower() in query.lower() and len(query.split()) >= 4:
            return query
        if len(query.split()) < 3:
            return f"{query} {subtopic} in context of {main_topic}"
        if subtopic.lower() in query.lower() and main_topic.lower() not in query.lower():
            return f"{query} {main_topic}"
        if main_topic.lower() in query.lower() and subtopic.lower() not in query.lower():
            if "overview" not in query.lower() and "introduction" not in query.lower():
                return f"{subtopic}: {query}"
        return query
        
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

