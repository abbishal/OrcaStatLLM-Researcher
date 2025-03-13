import arxiv
import requests
import pdfplumber
from typing import List, Dict
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.rate_limiter import RateLimitHandler
from modules.utils.citation import SourceReference

class ArxivClient:
    def __init__(self, rate_limiter: RateLimitHandler):
        self.rate_limiter = rate_limiter
    
    async def fetch_arxiv_papers(self, query: str, max_results=5, buffer: AsyncBuffer = None, references: dict = None) -> List[Dict]:
        if buffer is None:
            buffer = AsyncBuffer(verbose=False)
        
        buffer.add_log(f"Searching arXiv for papers related to: {query}", high_level=True)
        await self.rate_limiter.wait_if_needed("arxiv")
        
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            results = []
            
            for result in client.results(search):
                paper_info = {
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary,
                    "published": result.published.strftime("%Y-%m-%d") if result.published else None,
                    "url": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "arxiv_id": result.entry_id.split('/')[-1].split('v')[0]
                }
                
                if references is not None:
                    arxiv_ref = SourceReference(
                        title=paper_info["title"],
                        url=paper_info["pdf_url"],
                        authors=paper_info["authors"],
                        publication_date=paper_info["published"],
                        source_type="arxiv"
                    )
                    arxiv_ref.relevance_score = 0.9
                    arxiv_ref.calculate_scores()
                    references[paper_info["pdf_url"]] = arxiv_ref
                
                results.append(paper_info)
            
            buffer.add_log(f"Found {len(results)} arXiv papers related to '{query}'")
            return results
            
        except Exception as e:
            buffer.add_log(f"Error fetching arXiv papers: {str(e)}", high_level=True)
            return []
    
    async def download_and_parse_arxiv_paper(self, paper_info: Dict, buffer: AsyncBuffer, url_content_cache: dict) -> str:
        try:
            pdf_url = paper_info["pdf_url"]
            if pdf_url in url_content_cache:
                buffer.add_log(f"Using cached content for arXiv paper: {paper_info['title']}")
                return url_content_cache[pdf_url]
            
            buffer.add_log(f"Downloading arXiv paper: {paper_info['title']}", high_level=True)
            
            from pathlib import Path
            temp_dir = Path.home() / ".orcallm" / "temp"
            temp_file_path = temp_dir / f"arxiv_{paper_info['arxiv_id']}.pdf"
            
            if not temp_file_path.exists():
                response = requests.get(pdf_url, stream=True)
                if response.status_code != 200:
                    buffer.add_log(f"Failed to download PDF: {response.status_code}")
                    return ""
                
                with open(temp_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            buffer.add_log(f"Extracting text from arXiv paper: {paper_info['title']}", high_level=True)
            
            with pdfplumber.open(temp_file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            
            url_content_cache[pdf_url] = text
            return text
            
        except Exception as e:
            buffer.add_log(f"Error parsing arXiv paper: {str(e)}", high_level=True)
            return ""
