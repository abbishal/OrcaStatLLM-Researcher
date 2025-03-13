import json
from typing import Dict, List, Any, Callable, Awaitable
from modules.utils.citation import SourceReference
import asyncio

class ArxivResearcher:
    def __init__(self, process_query, arxiv_client, article_storage, references, citation_manager, literature_enhancer, url_content_cache):
        self.process_query = process_query
        self.arxiv_client = arxiv_client
        self.article_storage = article_storage
        self.references = references
        self.citation_manager = citation_manager
        self.literature_enhancer = literature_enhancer
        self.url_content_cache = url_content_cache
        
    async def research_arxiv_papers(self, topic: str, buffer: Any, academic_sources: Dict) -> Dict:

        buffer.add_log(f"Researching arXiv papers on: {topic}", high_level=True)
        
        try:
            try:
                specific_search = self.arxiv_client.fetch_arxiv_papers(topic, max_results=3, 
                                                                    buffer=buffer, 
                                                                    references=self.references)
                broader_term = topic.split()[0] if ' ' in topic else topic
                broader_search = self.arxiv_client.fetch_arxiv_papers(broader_term, max_results=2, 
                                                                    buffer=buffer, 
                                                                    references=self.references)
                specific_results, broader_results = await asyncio.gather(specific_search, broader_search, 
                                                                        return_exceptions=True)
                arxiv_results = []
                
                if not isinstance(specific_results, Exception):
                    arxiv_results.extend(specific_results)
                    
                if not isinstance(broader_results, Exception):
                    for paper in broader_results:
                        if not any(p.get('arxiv_id') == paper.get('arxiv_id') for p in arxiv_results):
                            arxiv_results.append(paper)
                
            except Exception as e:
                buffer.add_log(f"Error fetching arXiv papers: {str(e)}", high_level=True)
                arxiv_results = []
                
            if not arxiv_results or len(arxiv_results) == 0:
                buffer.add_log("No arXiv papers found after searches", high_level=True)
                return {"arxiv_papers": [], "insights": "", "citations": [], "paper_summaries": [], "article_ids": []}
                
            buffer.add_log(f"Found {len(arxiv_results)} arXiv papers", high_level=True)
            validated_results = []
            for paper in arxiv_results:
                try:
                    validated_paper = {
                        "title": self._safe_get_title(paper, topic, "arXiv Paper on"),
                        "authors": paper.get("authors") or ["Unknown Author"],
                        "published": paper.get("published") or "n.d.",
                        "arxiv_id": paper.get("arxiv_id") or "unknown_id",
                        "pdf_url": paper.get("pdf_url") or "",
                        "url": paper.get("pdf_url") or ""  # Add url field for consistent tracking
                    }
                    if validated_paper["pdf_url"]:
                        validated_results.append(validated_paper)
                except Exception as e:
                    buffer.add_log(f"Error validating arXiv paper: {str(e)}", high_level=True)
                    continue
                    
            arxiv_results = validated_results
            if not arxiv_results:
                buffer.add_log("No valid arXiv papers found after validation", high_level=True)
                return {"arxiv_papers": [], "insights": "", "citations": [], "paper_summaries": [], "article_ids": []}
            paper_tasks = []
            for paper in arxiv_results[:3]:  # Process top 3 papers
                paper_tasks.append(self._process_arxiv_paper(paper, topic, buffer))
            paper_results = await asyncio.gather(*paper_tasks, return_exceptions=True)
            paper_summaries = []
            stored_article_ids = []
            
            for result in paper_results:
                if not isinstance(result, Exception) and result:
                    paper_summaries.append(result["summary"])
                    stored_article_ids.append(result["article_id"])
            if not paper_summaries:
                buffer.add_log("No valid paper summaries generated after processing", high_level=True)
                return {"arxiv_papers": arxiv_results, "insights": "", "citations": [], 
                        "paper_summaries": [], "article_ids": []}
            paper_insights = await self._generate_literature_review(topic, paper_summaries, buffer)
            paper_citations = self._create_arxiv_citations(arxiv_results)
            self._update_tracking_counts(len(paper_summaries))
            
            initial_insights = {
                "arxiv_papers": arxiv_results,
                "insights": paper_insights,
                "citations": paper_citations,
                "paper_summaries": paper_summaries,
                "article_ids": stored_article_ids
            }
            academic_sources["arxiv_papers"] = arxiv_results
            if hasattr(buffer, 'time_critical') and buffer.time_critical:
                return initial_insights
            try:
                enhanced_insights = await self.literature_enhancer.enhance_literature_review(
                    topic, initial_insights, buffer, self.process_query
                )
            except Exception:
                enhanced_insights = initial_insights
                
            return enhanced_insights
            
        except Exception as e:
            buffer.add_log(f"Error researching arXiv papers: {str(e)}", high_level=True)
            return {"arxiv_papers": [], "insights": "", "citations": [], 
                   "paper_summaries": [], "article_ids": []}
                   
    async def _process_arxiv_paper(self, paper, topic, buffer):

        try:
            buffer.add_log(f"Processing arXiv paper: {paper['title']}", high_level=True)
            paper_url = paper['pdf_url']
            if self.article_storage.has_article(paper_url):
                buffer.add_log(f"Using previously stored arxiv paper: {paper['title']}")
                article_metadata = self.article_storage.get_article_by_url(paper_url)
                article_id = article_metadata["id"]
                paper_content = self.article_storage.get_article_content(article_id)
                summary = article_metadata.get("metadata", {}).get("summary", "")
                if not summary:
                    summary_prompt = self._generate_paper_summary_prompt(paper, paper_content, topic)
                    summary = await self.process_query(summary_prompt, buffer)
                    self.article_storage.add_summary_to_article(article_id, summary)
            else:
                paper_content = await self.arxiv_client.download_and_parse_arxiv_paper(
                    paper, buffer, self.url_content_cache
                )
                
                if not paper_content:
                    return None
                article_id = self.article_storage.store_article(
                    url=paper_url,
                    title=paper['title'],
                    content=paper_content,
                    source_type="arxiv",
                    metadata={
                        "authors": paper['authors'],
                        "published": paper['published'],
                        "arxiv_id": paper['arxiv_id'],
                        "topic": topic
                    }
                )
                summary_prompt = self._generate_paper_summary_prompt(paper, paper_content, topic)
                summary = await self.process_query(summary_prompt, buffer)
                self.article_storage.add_summary_to_article(article_id, summary)
            
            return {
                "title": paper['title'],
                "authors": paper['authors'],
                "published": paper['published'],
                "summary": summary,
                "article_id": article_id
            }
        except Exception as e:
            buffer.add_log(f"Error processing arXiv paper: {str(e)}", high_level=True)
            return None
            
    async def _generate_literature_review(self, topic, paper_summaries, buffer):

        try:
            lit_review_prompt = f"""
Synthesize these paper summaries into a cohesive 300-word literature review on "{topic}":

{chr(10).join([f"Paper {i+1}: {p['title']} - {p['summary'][:300]}..." for i, p in enumerate(paper_summaries)])}

Focus on common themes, contradictions, and research gaps. Use academic citation style [Author, YYYY].
"""
            return await self.process_query(lit_review_prompt, buffer)
        except Exception as e:
            buffer.add_log(f"Error generating literature review: {str(e)}", high_level=True)
            return f"A review of {len(paper_summaries)} academic papers related to {topic}."
    
    def _create_arxiv_citations(self, arxiv_results):

        citations = []
        try:
            for paper in arxiv_results:
                citation = f"{', '.join(paper['authors'])} ({paper['published'] if paper['published'] else 'n.d.'}). {paper['title']}. arXiv preprint arXiv:{paper['arxiv_id']}."
                citations.append(citation)
                arxiv_ref = self.references.get(paper['pdf_url'])
                if arxiv_ref:
                    self.citation_manager.add_reference(arxiv_ref)
        except Exception:
            pass
        return citations
        
    def _update_tracking_counts(self, count):

        if hasattr(self, 'url_tracking'):
            self.url_tracking['arxiv_count'] += count

    def _generate_paper_summary_prompt(self, paper: Dict, paper_content: str, topic: str) -> str:

        return f"""
Summarize this academic paper for a literature review on "{topic}":

Title: {paper['title']}
Authors: {', '.join(paper['authors'])}
Published: {paper['published']}

Paper excerpt:
{paper_content[:2000]}...

In 150-200 words, summarize:
1. Main research question/objective
2. Key methodology
3. Primary findings
4. Relevance to {topic}
"""

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

