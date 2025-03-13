import json
import re
from typing import Dict, List, Any, Callable, Awaitable
from modules.clients.literature_review_enhancer import LiteratureReviewEnhancer
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.citation import SourceReference
import asyncio
class AcademicResearcher:
    def __init__(self, process_query, search_client, article_storage, references, citation_manager, web_scraper=None):
        self.process_query = process_query
        self.search_client = search_client
        self.article_storage = article_storage
        self.references = references
        self.citation_manager = citation_manager
        self.literature_enhancer = LiteratureReviewEnhancer()
        self.web_scraper = web_scraper
        self.academic_dorks = [
            'site:*.edu filetype:pdf "{topic}"',
            'site:*.gov filetype:pdf "{topic}"',
            'site:*.ac filetype:pdf "{topic}"', 
            'site:researchgate.net filetype:pdf "{topic}"',
            'site:springer.com filetype:pdf "{topic}"',
            'site:arxiv.org filetype:pdf "{topic}"',
            'site:sciencedirect.com "{topic}"',
            'site:jstor.org "{topic}"',
            'site:springer.com "{topic}"',
            'site:ieeexplore.ieee.org "{topic}"',
            'site:mdpi.com "{topic}"',
            'site:ncbi.nlm.nih.gov "{topic}"',
            'site:scielo.org "{topic}"',
            'site:papers.ssrn.com "{topic}"'
        ]
        
    async def research_academic_papers_with_dorks(self, topic: str, buffer: Any, academic_sources: Dict) -> Dict:

        buffer.add_log(f"Researching academic papers using Google Dorks for: {topic}", high_level=True)
        if not self.web_scraper:
            buffer.add_log("ERROR: Web scraper not available for academic research. Will attempt to proceed.", high_level=True)
        cache_key = f"academic_keywords_{topic.replace(' ', '_')}"
        optimized_keywords = await self._generate_academic_search_keywords(topic, buffer, cache_key)
        buffer.add_log(f"Using optimized academic search keywords: {optimized_keywords[:3]}", high_level=True)
        
        academic_pdfs = []
        try:
            tasks = []
            selected_dorks = self.academic_dorks[:4]  # Limit to first 4 dorks for speed
            
            for keyword in optimized_keywords[:2]:  # Use top 2 optimized keywords (faster)
                for dork in selected_dorks[:2]:  # Further limit dorks per keyword (faster)
                    query = dork.format(topic=keyword)
                    tasks.append(self._process_academic_dork(query, academic_pdfs, topic, buffer))
            batch_size = 3  # Process 3 dorks at a time for speed+stability
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                await asyncio.gather(*batch)
                if len(academic_pdfs) >= 4:
                    buffer.add_log(f"Collected {len(academic_pdfs)} academic PDFs, stopping search for efficiency", high_level=True)
                    break
            if len(academic_pdfs) > 5:
                academic_pdfs = academic_pdfs[:5]
                
            academic_sources["academic_pdfs"] = academic_pdfs
            buffer.add_log(f"Successfully collected {len(academic_pdfs)} academic PDFs", high_level=True)
            return {"academic_pdfs": academic_pdfs}
            
        except Exception as e:
            buffer.add_log(f"Error in academic papers research with dorks: {str(e)}", high_level=True)
            return {"academic_pdfs": []}
    
    async def _process_academic_dork(self, query, academic_pdfs, topic, buffer):

        buffer.add_log(f"Using Google Dork: {query}", high_level=True)
        search_results = await self.search_client.google_search(query, buffer)
        if not search_results:
            buffer.add_log(f"No search results for dork: {query}")
            return
            
        buffer.add_log(f"Found {len(search_results)} search results for dork: {query}")
        for result in search_results[:2]:
            url = result.get("link")
            if not url or not url.startswith(("http://", "https://")):
                continue
            if any(pdf.get("url", "") == url for pdf in academic_pdfs):
                continue
            
            title = self._safe_get_title(result, topic, "PDF on")
            
            try:
                if self.article_storage.has_article(url):
                    article_metadata = self.article_storage.get_article_by_url(url)
                    article_id = article_metadata["id"]
                    content = self.article_storage.get_article_content(article_id)
                    summary = article_metadata.get("metadata", {}).get("summary")
                    if not summary:  # Generate new summary if needed
                        summary = await self._summarize_content(content, "PDF", topic, buffer)
                        self.article_storage.add_summary_to_article(article_id, summary)
                else:
                    if not self.web_scraper:
                        buffer.add_log("Web scraper still not available, skipping PDF", high_level=True)
                        continue
                        
                    content = await self.web_scraper.scrape_url(url, buffer)
                    if not content or len(content) < 500:  # Ensure we have meaningful content
                        continue
                    
                    article_id = self.article_storage.store_article(
                        url=url,
                        title=title,
                        content=content,
                        source_type="pdf",
                        metadata={
                            "topic": topic,
                            "query": query,
                            "snippet": result.get("snippet", "")
                        }
                    )
                    summary = await self._summarize_content(content, "PDF", topic, buffer)
                    self.article_storage.add_summary_to_article(article_id, summary)
                source_ref = SourceReference(
                    title=title,
                    url=url,
                    source_type="pdf"
                )
                source_ref.relevance_score = 0.9  # Academic PDFs are highly relevant
                source_ref.calculate_scores()
                self.references[url] = source_ref
                self.citation_manager.add_reference(source_ref)
                academic_pdfs.append({
                    "source": f"{title} - {url}",
                    "content": content[:5000] if len(content) > 5000 else content,  # Truncate content for memory efficiency
                    "summary": summary,
                    "source_type": "pdf",
                    "article_id": article_id,
                    "title": title,
                    "url": url
                })
                if len(academic_pdfs) >= 6:
                    break
            except Exception as e:
                buffer.add_log(f"Error processing academic PDF {url}: {str(e)}")
                continue
    
    async def _generate_academic_search_keywords(self, topic: str, buffer: Any, cache_key: str = None) -> List[str]:

        buffer.add_log("Generating optimized academic search keywords", high_level=True)
        
        try:
            topic_words = topic.split()
            if len(topic_words) <= 2:
                keywords = [topic]
            else:
                prompt = f"""
Generate 3-4 concise academic search phrases based on this topic: "{topic}"

Each phrase should:
1. Be 2-3 words long (short and focused)
2. Capture key academic concepts
3. Use scholarly terminology
4. Be effective for finding academic papers

Format your response as a JSON array of strings:
["keyword1", "keyword2", "keyword3"]
Only return the JSON array.
"""
                
                response = await self.process_query(prompt, buffer)
                try:
                    json_str = response
                    if "```json" in response:
                        json_str = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        json_str = response.split("```")[1].strip()
                        
                    keywords = json.loads(json_str)
                    if not keywords or not isinstance(keywords, list):
                        raise ValueError("Invalid keyword format returned")
                        
                except Exception as e:
                    buffer.add_log(f"Error parsing academic keywords: {str(e)}. Using fallback keywords.")
                    if len(topic_words) > 5:
                        keywords = [' '.join(topic_words[:2]), ' '.join(topic_words[:3])]
                    else:
                        keywords = [' '.join(topic_words[:2]), topic]
            if topic not in keywords:
                keywords.append(topic)
            academic_variants = [f"{topic} research", f"{topic} study", f"{topic} methodology"]
            for variant in academic_variants:
                if len(keywords) < 5 and not any(variant.lower() in kw.lower() for kw in keywords):
                    keywords.append(variant)
                    
            buffer.add_log(f"Generated {len(keywords)} academic search keywords", high_level=True)
            return keywords
            
        except Exception as e:
            buffer.add_log(f"Error generating academic search keywords: {str(e)}", high_level=True)
            words = topic.split()
            if len(words) > 3:
                return [' '.join(words[:2]), ' '.join(words[:3]), topic]
            return [topic, f"{topic} research"]
            
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
            
    def combine_academic_insights(self, arxiv_insights: Dict, academic_insights: Dict, 
                                  stats_insights: Dict, doi_papers: Dict, buffer: Any) -> Dict:

        buffer.add_log("Combining insights from various academic sources", high_level=True)
        arxiv_insights = self._ensure_valid_insights_structure(arxiv_insights)
        academic_insights = self._ensure_valid_insights_structure(academic_insights)
        stats_insights = self._ensure_valid_insights_structure(stats_insights)
        doi_papers = self._ensure_valid_insights_structure(doi_papers)
        
        combined_insights = {
            "insights": "",
            "citations": [],
            "paper_summaries": [],
            "article_ids": []
        }
        combined_insights["insights"] += arxiv_insights.get("insights", "")
        combined_insights["insights"] += academic_insights.get("insights", "")
        combined_insights["insights"] += stats_insights.get("insights", "")
        combined_insights["insights"] += doi_papers.get("insights", "")
        combined_insights["citations"] += arxiv_insights.get("citations", [])
        combined_insights["citations"] += academic_insights.get("citations", [])
        combined_insights["citations"] += stats_insights.get("citations", [])
        combined_insights["citations"] += doi_papers.get("citations", [])
        combined_insights["paper_summaries"] += arxiv_insights.get("paper_summaries", [])
        combined_insights["paper_summaries"] += academic_insights.get("paper_summaries", [])
        combined_insights["paper_summaries"] += stats_insights.get("paper_summaries", [])
        combined_insights["paper_summaries"] += doi_papers.get("paper_summaries", [])
        combined_insights["article_ids"] += arxiv_insights.get("article_ids", [])
        combined_insights["article_ids"] += academic_insights.get("article_ids", [])
        combined_insights["article_ids"] += stats_insights.get("article_ids", [])
        combined_insights["article_ids"] += doi_papers.get("article_ids", [])
        for i, summary in enumerate(combined_insights["paper_summaries"]):
            if not summary.get("title"):
                combined_insights["paper_summaries"][i]["title"] = f"Untitled Paper {i+1}"
        
        return combined_insights
        
    def _ensure_valid_insights_structure(self, insights: Dict) -> Dict:

        if not insights:
            return {
                "insights": "",
                "citations": [],
                "paper_summaries": [],
                "article_ids": []
            }
        for key in ["insights", "citations", "paper_summaries", "article_ids"]:
            if key not in insights:
                insights[key] = [] if key != "insights" else ""
        if not isinstance(insights["paper_summaries"], list):
            insights["paper_summaries"] = []
        if not isinstance(insights["article_ids"], list):
            insights["article_ids"] = []
            
        return insights
        
    async def enhance_academic_citations(self, combined_insights: Dict, buffer: Any, academic_sources: Dict, research_data: Dict):

        buffer.add_log("Enhancing academic citations", high_level=True)
        combined_insights["citations"] = await self.literature_enhancer.validate_citations(
            combined_insights, buffer, self.process_query
        )
        buffer.add_log("Searching for additional academic citations to enhance reference list", high_level=True)
        topic = research_data.get("topic", "")
        
        if topic:
            additional_papers = []
            if len(academic_sources.get("doi_papers", [])) < 3:
                try:
                    buffer.add_log("Finding additional academic papers with DOIs", high_level=True)
                    additional_doi_papers = await self.doi_researcher.research_doi_papers(topic, buffer, academic_sources)
                    if additional_doi_papers and additional_doi_papers.get("doi_papers"):
                        additional_papers.extend(additional_doi_papers.get("doi_papers", []))
                        buffer.add_log(f"Found {len(additional_doi_papers.get('doi_papers', []))} additional DOI papers", high_level=True)
                except Exception as e:
                    buffer.add_log(f"Error finding additional DOI papers: {str(e)}")
            if len(academic_sources.get("arxiv_papers", [])) < 3:
                try:
                    buffer.add_log("Finding additional arXiv papers", high_level=True)
                    additional_arxiv_result = await self.arxiv_researcher.research_arxiv_papers(topic, buffer, academic_sources)
                    if additional_arxiv_result and additional_arxiv_result.get("arxiv_papers"):
                        for paper in additional_arxiv_result.get("arxiv_papers", []):
                            if not any(p.get('title') == paper.get('title') for p in academic_sources.get("arxiv_papers", [])):
                                academic_sources["arxiv_papers"].append(paper)
                                combined_insights["citations"].append(
                                    f"{', '.join(paper['authors'])} ({paper['published'] if paper['published'] else 'n.d.'}). {paper['title']}. arXiv preprint arXiv:{paper['arxiv_id']}."
                                )
                                buffer.add_log(f"Added citation for arXiv paper: {paper['title']}", high_level=True)
                except Exception as e:
                    buffer.add_log(f"Error finding additional arXiv papers: {str(e)}")
            if additional_papers:
                buffer.add_log(f"Added {len(additional_papers)} additional academic references", high_level=True)
                for paper in additional_papers:
                    if "source" in paper and "summary" in paper:
                        source_parts = paper["source"].split(" - ")
                        if len(source_parts) > 1:
                            title = source_parts[0].strip()
                            url = source_parts[1].strip()
                            
                            citation = f"{title}. Retrieved from {url}"
                            if citation not in combined_insights["citations"]:
                                combined_insights["citations"].append(citation)
        for i, citation in enumerate(combined_insights["citations"]):
            doi_match = re.search(r'DOI:?\s*(\d+\.\d+/[^,\s]+)', citation, re.IGNORECASE)
            if doi_match and "doi.org" not in citation:
                doi = doi_match.group(1)
                combined_insights["citations"][i] = citation.replace(
                    doi_match.group(0), 
                    f"DOI: {doi}. https://doi.org/{doi}"
                )
            if citation.startswith("http"):
                url = citation
                if url in self.references:
                    ref = self.references[url]
                    combined_insights["citations"][i] = ref.format_citation('apa')
        combined_insights["citations"].sort(key=lambda x: 0 if any(
            academic_kw in x.lower() for academic_kw in 
            ['doi:', 'journal', 'conference', 'proceedings', 'arxiv', 'university', 'dissertation']
        ) else 1)
        
        buffer.add_log(f"Enhanced {len(combined_insights['citations'])} academic citations", high_level=True)
        research_data["academic_sources"] = academic_sources
        research_data["academic_insights"] = combined_insights
        
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

    def combine_academic_insights(self, arxiv_insights: Dict, academic_insights: Dict, 
                             stats_insights: Dict, doi_papers: Dict,
                             buffer: AsyncBuffer = None) -> Dict:
        """Combine insights from various academic sources"""
        if buffer:
            buffer.add_log("Combining insights from various academic sources", high_level=True)
        
        combined = {}
        
        # Process ArXiv insights
        combined["arxiv_papers"] = arxiv_insights.get("arxiv_papers", [])
        combined["article_ids"] = arxiv_insights.get("article_ids", [])

        # Process DOI papers
        combined["doi_papers"] = doi_papers.get("doi_papers", [])
        
        # Handle statistics insights
        combined["statistics_sources"] = stats_insights.get("statistics_sources", [])
        
        # Process academic PDFs
        combined["academic_pdfs"] = academic_insights.get("academic_pdfs", [])
        
        # Combine paper summaries
        paper_summaries = []
        
        # Add ArXiv summaries
        arxiv_summaries = arxiv_insights.get("paper_summaries", [])
        if arxiv_summaries:
            for summary in arxiv_summaries:
                # Check if summary is a dictionary before calling get()
                if isinstance(summary, dict):
                    if not summary.get("title"):
                        continue
                    paper_summaries.append(summary)
                elif isinstance(summary, str):
                    # Handle case where summary is a string
                    paper_summaries.append({"title": "ArXiv Paper Summary", "summary": summary})
        
        # Add DOI summaries
        doi_summaries = doi_papers.get("paper_summaries", [])
        if doi_summaries:
            for summary in doi_summaries:
                # Check if summary is a dictionary before calling get()
                if isinstance(summary, dict):
                    if not summary.get("title"):
                        continue
                    paper_summaries.append(summary)
                elif isinstance(summary, str):
                    # Handle case where summary is a string
                    paper_summaries.append({"title": "DOI Paper Summary", "summary": summary})
        
        # Add academic PDF summaries
        academic_summaries = academic_insights.get("paper_summaries", [])
        if academic_summaries:
            for summary in academic_summaries:
                # Check if summary is a dictionary before calling get()
                if isinstance(summary, dict):
                    if not summary.get("title"):
                        continue
                    paper_summaries.append(summary)
                elif isinstance(summary, str):
                    # Handle case where summary is a string
                    paper_summaries.append({"title": "Academic Paper Summary", "summary": summary})
        
        combined["paper_summaries"] = paper_summaries
        
        # Combine literature reviews and paper insights
        reviews = []
        
        arxiv_review = arxiv_insights.get("insights", "")
        if arxiv_review:
            reviews.append(f"ArXiv Literature:\n{arxiv_review}")
        
        doi_review = doi_papers.get("insights", "")
        if doi_review:
            reviews.append(f"DOI Literature:\n{doi_review}")
        
        academic_review = academic_insights.get("insights", "")
        if academic_review:
            reviews.append(f"Academic Literature:\n{academic_review}")
        
        stats_review = stats_insights.get("insights", "")
        if stats_review:
            reviews.append(f"Statistical Sources:\n{stats_review}")
        
        combined["literature_review"] = "\n\n".join(reviews)
        
        # Combine citations
        all_citations = []
        all_citations.extend(arxiv_insights.get("citations", []))
        all_citations.extend(doi_papers.get("citations", []))
        all_citations.extend(academic_insights.get("citations", []))
        combined["citations"] = all_citations
        
        return combined
