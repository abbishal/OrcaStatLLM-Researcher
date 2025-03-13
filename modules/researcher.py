import os
import time
import uuid
import json
import asyncio
import datetime
import logging
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import re
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.rate_limiter import RateLimitHandler
from modules.utils.citation import Citation, SourceReference
from modules.clients.gemini_client import GeminiClient
from modules.clients.search_client import SearchClient
from modules.clients.wikipedia_client import WikipediaClient
from modules.clients.arxiv_client import ArxivClient
from modules.clients.web_scraper import WebScraper
from modules.visualization.visualizer import Visualizer
from modules.document.markdown_generator import MarkdownGenerator
from modules.document.pdf_converter import PDFConverter
from modules.document.table_generator import TableGenerator
from modules.clients.literature_review_enhancer import LiteratureReviewEnhancer
from modules.utils.article_storage import ArticleStorage
from modules.clients.news_client import NewsClient
from modules.clients.academic_search import search_paper1, SciHubLink
from modules.utils.content_optimizer import ContentOptimizer
from modules.core.config import setup_directories, DATA_DIR, LOG_DIR, LOG_FILE, RESEARCH_DIR, CACHE_DIR, TEMP_DIR, FIGURE_DIR
from modules.core.research_data import ResearchDataManager
from modules.core.url_tracking import URLTracker
from modules.core.progress_tracker import ProgressTracker
from modules.research.topic_analyzer import TopicAnalyzer
from modules.research.academic_researcher import AcademicResearcher
from modules.research.content_generator import ContentGenerator
from modules.research.subtopic_researcher import SubtopicResearcher
from modules.research.statistics_researcher import StatisticsResearcher
from modules.research.doi_researcher import DOIResearcher
from modules.research.arxiv_researcher import ArxivResearcher
from modules.utils.error_handler import log_exception

setup_directories()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("OrcaStatLLM-Scientist")

class OrcaStatLLMScientist:
    def __init__(self, research_id: Optional[str] = None, verbose: bool = False):
        self.research_id = research_id or str(uuid.uuid4())
        self.research_dir = RESEARCH_DIR / self.research_id
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.research_data_file = self.research_dir / "research_data.json"
        self.model_weights = {"gemini": 1.0}
        self.verbose = verbose
        self.rate_limiter = RateLimitHandler()
        self.cse_fallback_count = 0
        self.url_content_cache = {}
        self.already_scraped_urls = set()
        self.visited_search_queries = set()
        self.resource_images = {}
        self.references = {}
        self.tables = []
        self.figures = {}
        self.citation_format = "apa"
        self.citation_manager = Citation(style="apa")
        self.max_depth = 3
        self.max_sources_per_subtopic = 8
        self.max_academic_papers = 5
        self.result_cache = {}
        self.cache_ttl = 3600  
        self.content_optimizer = ContentOptimizer()
        self.semaphore = asyncio.Semaphore(5)
        self.data_manager = ResearchDataManager(self.research_data_file)
        self.research_data = self.data_manager.load_research_data()
        self.url_tracker = URLTracker()
        self.url_tracking = self.url_tracker.get_tracking_data()
        self.academic_sources = {
            'arxiv_papers': [],
            'doi_papers': [],
            'academic_pdfs': [],
            'statistics_sources': []
        }
        
        self.gemini_client = GeminiClient()
        self.search_client = SearchClient(self.rate_limiter)
        self.wikipedia_client = WikipediaClient(self.rate_limiter)
        self.arxiv_client = ArxivClient(self.rate_limiter)
        self.web_scraper = WebScraper(self.rate_limiter)
        self.visualizer = Visualizer(self.research_dir)
        self.markdown_generator = MarkdownGenerator()
        self.pdf_converter = PDFConverter()
        self.table_generator = TableGenerator()
        self.literature_enhancer = LiteratureReviewEnhancer()
        
        self.article_storage = ArticleStorage(CACHE_DIR / "articles")
        
        self.news_client = NewsClient(self.rate_limiter)
        
        logger.info(f"Initialized OrcaStatLLM Scientist with research ID: {self.research_id}")

        self._setup_url_tracking()
    
        self.progress_tracker = ProgressTracker()
        self.progress = self.progress_tracker.get_initial_progress()

        self.topic_analyzer = TopicAnalyzer(self.process_query, self.news_client)
        self.academic_researcher = AcademicResearcher(
            self.process_query, 
            self.search_client, 
            self.article_storage, 
            self.references,
            self.citation_manager,
            self.web_scraper  
        )
        self.content_generator = ContentGenerator(self.process_query)
        self.subtopic_researcher = SubtopicResearcher(
            self.process_query,
            self.web_scraper,
            self.wikipedia_client,
            self.search_client,
            self.article_storage,
            self.references,
            self.citation_manager,
            self.url_tracking
        )
        self.subtopic_researcher.visualizer = self.visualizer

        self.statistics_researcher = StatisticsResearcher(
            self.process_query,
            self.search_client,
            self.web_scraper,
            self.article_storage,
            self.references,
            self.citation_manager
        )
        self.doi_researcher = DOIResearcher(
            self.process_query,
            self.web_scraper,
            self.article_storage,
            self.references,
            self.citation_manager,
            self.url_tracking
        )
        self.arxiv_researcher = ArxivResearcher(
            self.process_query,
            self.arxiv_client,
            self.article_storage,
            self.references,
            self.citation_manager,
            self.literature_enhancer,
            self.url_content_cache
        )

    def _setup_url_tracking(self):
        self.url_tracker.setup_tracking_for_scraper(self.web_scraper, self.research_data, self.save_research_data)

    def save_research_data(self):
        self.research_data["last_updated"] = datetime.datetime.now().isoformat()
        self.research_data["references"] = {url: ref.to_dict() for url, ref in self.references.items()}
        self.research_data["academic_sources"] = self.academic_sources
        self.research_data["url_tracking"] = self.url_tracker.get_tracking_data()
        self.data_manager.save_research_data(self.research_data)

    def hash_url(self, url):
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()

    def get_cache_path(self, url):
        hashed = self.hash_url(url)
        return CACHE_DIR / f"{hashed}.json"

    def check_cache(self, url):
        cache_path = self.get_cache_path(url)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    if data.get('timestamp', 0) > time.time() - 86400:
                        content = data.get('content')
                        if content and hasattr(self, 'content_optimizer'):
                            return self.content_optimizer.filter_redundant_content(content)
                        return content
            except Exception:
                pass
        return None

    async def process_query_with_cache(self, query: str, buffer: AsyncBuffer = None, cache_key: str = None) -> str:
        if buffer is None:
            buffer = AsyncBuffer(verbose=self.verbose)
        
        cache_key = cache_key or f"query_{hash(query)}"
        if hasattr(self, 'result_cache') and cache_key in self.result_cache:
            result, timestamp = self.result_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
        
        async with self.semaphore:
            result = await self.gemini_client.query_gemini(query, buffer)
            if hasattr(self, 'result_cache'):
                self.result_cache[cache_key] = (result, time.time())
            return result

    async def process_query(self, query: str, buffer: AsyncBuffer = None) -> str:
        if hasattr(self, 'result_cache'): 
            return await self.process_query_with_cache(query, buffer)
        
        if buffer is None:
            buffer = AsyncBuffer(verbose=self.verbose)
        
        result = await self.gemini_client.query_gemini(query, buffer)
        return result

    async def generate_research_paper(self, topic: str) -> str:
        buffer = AsyncBuffer(verbose=self.verbose)
        buffer.add_log(f"Starting research paper generation for: {topic}", high_level=True)
        try:
            self.url_tracking = self.url_tracker.reset_tracking()
            if hasattr(self, 'academic_researcher'):
                if not self.academic_researcher.web_scraper:
                    self.academic_researcher.web_scraper = self.web_scraper
                    buffer.add_log("Set web_scraper on academic_researcher", high_level=True)

            for researcher_name in ['subtopic_researcher', 'statistics_researcher', 'doi_researcher', 'arxiv_researcher']:
                if hasattr(self, researcher_name) and hasattr(getattr(self, researcher_name), '_update_tracking_counts'):
                    setattr(getattr(self, researcher_name), 'url_tracking', self.url_tracking)
            
            self.result_cache = {}
            self.url_content_cache = {}

            if hasattr(self, 'content_optimizer'):
                self.content_optimizer.processed_content_hashes.clear()

            self.progress = self.progress_tracker.reset_progress()
            self._update_progress_state(buffer)

            self.research_data["topic"] = topic
            self.research_data["status"] = "researching"
            self.research_data["url_tracking"] = self.url_tracking
            self.research_data["academic_sources"] = self.academic_sources
            self.research_data["progress"] = self.progress
            if "research_results" not in self.research_data:
                self.research_data["research_results"] = {}
            self.save_research_data()

            section_results = []
            combined_insights = {}
            stats_insights = {}
            subtopics_data = []
            
            self.progress = self.progress_tracker.update_step(1, "Topic Analysis", 
                                                           "Analyzing topic type and gathering contextual information",
                                                           ["Topic classification", "News relevance analysis", "Event detection"],
                                                           0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 1: Analyzing topic type and generating title concurrently", high_level=True)
            analysis_task = self.topic_analyzer.analyze_topic(topic, buffer)
            title_task = asyncio.create_task(self.generate_title(topic, buffer))
            event_analysis = await analysis_task
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            self.research_data["event_analysis"] = event_analysis if event_analysis else {}
            self.save_research_data()
            try:
                title = await title_task
                if not title:
                    title = event_analysis.get("title", "") if event_analysis else ""
                if not title:
                    title = f"Research Paper on {topic}"
            except Exception as e:
                buffer.add_log(f"Error generating title: {str(e)}", high_level=True)
                log_exception(e, "Error generating title", buffer, self.research_data, self.save_research_data)
                title = f"Research Paper on {topic}"
                
            self.research_data["title"] = title
            self.save_research_data()
            buffer.add_log("Steps 2-3: Running topic breakdown and subtopic identification concurrently", high_level=True)
            breakdown_task = asyncio.create_task(
                self.topic_analyzer.breakdown_topic(topic, buffer, self.research_data)
            )
            subtopics_task = asyncio.create_task(
                self.topic_analyzer.identify_subtopics(topic, buffer, self.research_data)
            )
            self.progress = self.progress_tracker.update_step(2, "Initial Research Planning", 
                                                             "Breaking down topic into searchable components",
                                                             ["Identifying key concepts", "Creating search strategies", "Formulating queries"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 2: Breaking down topic into searchable components", high_level=True)
            search_components = await breakdown_task
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            
            self.research_data["search_components"] = search_components
            self.save_research_data()
            self.progress = self.progress_tracker.update_step(3, "Topic Structuring", 
                                                             "Identifying and organizing research subtopics",
                                                             ["Analyzing topic dimensions", "Mapping content structure", "Planning research areas"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 3: Identifying subtopics", high_level=True)
            subtopics_data = await subtopics_task
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            self.progress = self.progress_tracker.update_step(4, "Academic Research", 
                                                             "Researching academic papers and incorporating scholarly insights",
                                                             ["Finding relevant papers", "Analyzing academic content", "Extracting key insights", "Collecting statistics"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 4: Parallel research of academic papers and statistics", high_level=True)

            academic_task = asyncio.create_task(
                self.academic_researcher.research_academic_papers_with_dorks(topic, buffer, self.academic_sources)
            )
            stats_task = asyncio.create_task(
                self.statistics_researcher.research_statistics_sources(topic, buffer, self.academic_sources)
            )
            doi_task = asyncio.create_task(
                self.doi_researcher.research_doi_papers(topic, buffer, self.academic_sources)
            )
            arxiv_task = asyncio.create_task(
                self.arxiv_researcher.research_arxiv_papers(topic, buffer, self.academic_sources)
            )
            
            buffer.add_log("Waiting for academic research tasks to complete", high_level=True)
            results = await asyncio.gather(academic_task, stats_task, doi_task, arxiv_task, 
                                          return_exceptions=True)
            academic_insights = {}
            stats_insights = {}
            doi_papers = {}
            arxiv_insights = {}
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    buffer.add_log(f"Error in academic research task #{i+1}: {str(result)}", high_level=True)
                else:
                    if i == 0:
                        academic_insights = result or {}
                    elif i == 1:
                        stats_insights = result or {}
                    elif i == 2:
                        doi_papers = result or {}
                    elif i == 3:
                        arxiv_insights = result or {}
            
            combined_insights = self.academic_researcher.combine_academic_insights(
                arxiv_insights, 
                academic_insights, 
                stats_insights,
                doi_papers,
                buffer
            )
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            
            self.research_data["academic_insights"] = combined_insights
            self.save_research_data()
            if subtopics_data:
                self.progress = self.progress_tracker.update_step(5, "Deep Research", 
                                                                "Researching and collecting data for each subtopic",
                                                                [f"Research: {subtopic_data['subtopic']}" for subtopic_data in subtopics_data[:3]],
                                                                0)
                if len(subtopics_data) > 3:
                    self.progress["subtasks"].append(f"Research: {len(subtopics_data) - 3} more subtopics")
                self._update_progress_state(buffer)
                
                buffer.add_log("Step 5: Researching subtopics in optimized batches", high_level=True)

                prioritized_subtopics = sorted(
                    subtopics_data, 
                    key=lambda x: self._estimate_subtopic_importance(x, topic),
                    reverse=True
                )
    
                if len(prioritized_subtopics) > 5:
                    buffer.add_log(f"Focusing on the {5} most important subtopics out of {len(prioritized_subtopics)}", high_level=True)
                    subtopics_to_research = prioritized_subtopics[:5]
                else:
                    subtopics_to_research = prioritized_subtopics
                
                section_results = []
                batch_size = 2 
                total_batches = (len(subtopics_to_research) + batch_size - 1) // batch_size
                
                for batch_idx in range(0, len(subtopics_to_research), batch_size):
                    batch_num = batch_idx // batch_size + 1
                    buffer.add_log(f"Processing subtopic batch {batch_num}/{total_batches}", high_level=True)
                    
                    batch_tasks = []
                    for i in range(batch_idx, min(batch_idx + batch_size, len(subtopics_to_research))):
                        subtopic_data = subtopics_to_research[i]
                        buffer.add_log(f"Starting research for subtopic {i+1}/{len(subtopics_to_research)}: {subtopic_data['subtopic']}", high_level=True)
                        task = asyncio.create_task(
                            self.subtopic_researcher.research_subtopic(topic, subtopic_data, buffer, combined_insights, self.progress)
                        )
                        batch_tasks.append((i, task))

                    for i, task in batch_tasks:
                        try:
                            section = await task
                            section_results.append(section)
                            self.research_data["research_results"][section["subtopic"]] = section
                            self.save_research_data()
                            
                            if i < 3:
                                self.progress["completed_subtasks"] = i + 1
                            else:
                                completion_percentage = (i - 2) / max(1, (len(subtopics_to_research) - 3))
                                self.progress["completed_subtasks"] = 3 + completion_percentage
                            self._update_progress_state(buffer)
                            if hasattr(self, 'content_optimizer') and len(section_results) >= 3:
                                if self.content_optimizer.has_sufficient_research(self.research_data):
                                    buffer.add_log("Sufficient research gathered for quality paper. Proceeding to content generation.", high_level=True)
                                    break
                            
                        except Exception as e:
                            buffer.add_log(f"Error researching subtopic {i+1}: {str(e)}", high_level=True)
                            log_exception(e, f"Error researching subtopic {i+1}", buffer, self.research_data, self.save_research_data)
                            section = {"subtopic": subtopics_to_research[i]["subtopic"], 
                                    "content": f"Limited information available on this subtopic."}
                            section_results.append(section)
                            self.research_data["research_results"][section["subtopic"]] = section
                            self.save_research_data()
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)

            buffer.add_log("Steps 6-7: Processing document components concurrently", high_level=True)
            tables_task = asyncio.create_task(
                self.generate_tables(topic, section_results, buffer, stats_insights)
            )
            abstract_task = asyncio.create_task(
                self.generate_abstract(topic, section_results, combined_insights, buffer)
            )
            conclusion_task = asyncio.create_task(
                self.generate_conclusion(topic, section_results, combined_insights, buffer)
            )
            
            self.progress = self.progress_tracker.update_step(6, "Data Organization", 
                                                             "Organizing research data into structured formats",
                                                             ["Analyzing data relationships", "Creating data tables", "Structuring information"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 6: Generating tables for data presentation", high_level=True)
            tables = await tables_task
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            
            self.research_data["tables"] = tables
            self.save_research_data()
            self.progress = self.progress_tracker.update_step(7, "Draft Creation", 
                                                             "Creating initial document sections",
                                                             ["Writing abstract", "Creating introduction", "Drafting conclusion"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 7: Generating abstract and conclusion", high_level=True)
            abstract, conclusion = await asyncio.gather(abstract_task, conclusion_task)
            
            self.progress["completed_subtasks"] = 3  
            self._update_progress_state(buffer)
            
            self.research_data["abstract"] = abstract
            self.research_data["conclusion"] = conclusion
            self.save_research_data()
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)

            self.progress = self.progress_tracker.update_step(8, "Document Assembly", 
                                                             "Assembling all components into a coherent document",
                                                             ["Combining sections", "Formatting content", "Structuring document"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 8: Generating final markdown document", high_level=True)
            markdown_file = await self.generate_markdown(topic, title, abstract, section_results, 
                                                      conclusion, combined_insights, tables, buffer)
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            
            self.research_data["markdown_file"] = markdown_file
            self.save_research_data()
            
            self.progress = self.progress_tracker.update_step(9, "References & Citations", 
                                                             "Finalizing citations and reference formatting",
                                                             ["Organizing citations", "Formatting references", "Verifying sources"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 9: Processing citations and references", high_level=True)
            await self.academic_researcher.enhance_academic_citations(combined_insights, buffer, self.academic_sources, self.research_data)
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            self.progress = self.progress_tracker.update_step(10, "Final Output", 
                                                             "Converting to final presentation format",
                                                             ["Formatting for PDF", "Generating final document", "Quality check"],
                                                             0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 10: Converting to PDF", high_level=True)
            pdf_file = await self.convert_to_pdf(markdown_file, buffer)
            
            self.progress = self.progress_tracker.complete_current_step()
            self._update_progress_state(buffer)
            
            if pdf_file:
                self.research_data["pdf_file"] = pdf_file
                self.research_data["status"] = "completed"
                self.save_research_data()
            
            buffer.add_log(f"Research paper generation completed. Files saved in: {self.research_dir}", high_level=True)
            
            return markdown_file
        except Exception as e:
            buffer.add_log(f"Error in research paper generation: {str(e)}", high_level=True)
            log_exception(e, "Error in research paper generation", buffer, self.research_data, self.save_research_data)
            return ""

    def _update_progress_state(self, buffer=None):
        if buffer:
            progress_percentage = int((self.progress["current_step"] / self.progress["max_steps"]) * 100)
            subtasks_progress = ""
            if self.progress["subtasks"]:
                completed = min(self.progress["completed_subtasks"], len(self.progress["subtasks"]))
                subtasks_fraction = f"{completed}/{len(self.progress['subtasks'])}"
                subtasks_progress = f" (Subtasks: {subtasks_fraction})"
                
            buffer.add_log(
                f"Progress update: Step {self.progress['current_step']}/{self.progress['max_steps']} "
                f"- {self.progress['step_name']} - {progress_percentage}%{subtasks_progress}",
                high_level=True
            )
        
        self.research_data["progress"] = self.progress
        self.save_research_data()

    async def generate_tables(self, topic: str, sections: List[Dict], buffer: AsyncBuffer, stats_insights: Dict) -> List[Dict]:
        if not sections or len(sections) < 2:
            buffer.add_log("Not enough sections to generate comparative tables", high_level=True)
            return []
            
        buffer.add_log("Generating tables for data presentation", high_level=True)
        table_candidates = []
        for section in sections:
            content = section['content']
            if (content.count('- ') > 5 or 
                content.count(':') > 5 or 
                content.count('%') > 3 or 
                content.lower().count(' comparison ') > 0 or
                content.lower().count(' versus ') > 0 or
                content.lower().count(' vs. ') > 0):
                
                table_candidates.append(section)
        
        if not table_candidates:
            buffer.add_log("No suitable content identified for tabular representation", high_level=True)
            return []
            
        tables = []
        for candidate in table_candidates[:2]:
            subtopic = candidate['subtopic']
            table_data = await self.table_generator.generate_table_from_text(
                candidate['content'], subtopic, buffer, self.process_query)
                
            if table_data:
                tables.append(table_data)
                buffer.add_log(f"Generated table for section: {subtopic}", high_level=True)
        
        if stats_insights:
            for stat in stats_insights.get("statistics_sources", []):
                table_data = await self.table_generator.generate_table_from_text(
                    stat['content'], stat['title'], buffer, self.process_query)
                if table_data:
                    tables.append(table_data)
                    buffer.add_log(f"Generated table from statistics source: {stat['title']}", high_level=True)
        
        buffer.add_log(f"Generated {len(tables)} tables for the research paper", high_level=True)
        return tables

    async def generate_abstract(self, topic: str, sections: List[Dict], 
                               combined_insights: Dict, buffer: AsyncBuffer) -> str:
        return await self.content_generator.generate_abstract(topic, sections, combined_insights, buffer)

    async def generate_conclusion(self, topic: str, sections: List[Dict], 
                                 combined_insights: Dict, buffer: AsyncBuffer) -> str:
        return await self.content_generator.generate_conclusion(topic, sections, combined_insights, buffer)

    async def generate_markdown(self, topic: str, title: str, abstract: str, sections: List[Dict], 
                              conclusion: str, combined_insights: Dict, tables: List[Dict],
                              buffer: AsyncBuffer) -> str:
        try:
            return await self.markdown_generator.generate_markdown(
                topic, title, abstract, sections, conclusion, buffer, self.research_dir, 
                self.visualizer.embed_image_base64, self.references, combined_insights, tables
            )
        except Exception as e:
            buffer.add_log(f"Error generating markdown: {str(e)}", high_level=True)
            short_name = self.shorten_filename(topic)
            markdown_file = self.research_dir / f"{short_name}_fallback.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n## Abstract\n\n{abstract}\n\n")
                for section in sections:
                    f.write(f"## {section['subtopic']}\n\n{section['content']}\n\n")
                f.write(f"## Conclusion\n\n{conclusion}\n\n")
            return str(markdown_file)

    async def convert_to_pdf(self, markdown_file: str, buffer: AsyncBuffer) -> str:
        return await self.pdf_converter.convert_to_pdf(markdown_file, buffer)

    async def generate_title(self, topic: str, buffer: AsyncBuffer) -> str:
        return await self.content_generator.generate_title(topic, buffer)
    
    def _estimate_subtopic_importance(self, subtopic_data: Dict[str, Any], main_topic: str) -> float:
        subtopic = subtopic_data.get('subtopic', '')
        description = subtopic_data.get('description', '') or ''
        
        if not subtopic:
            return 0.0
            
        score = 0.0
        words = len(subtopic.split())
        if 2 <= words <= 5:
            score += 0.2
        main_topic_words = set(main_topic.lower().split())
        subtopic_words = set(subtopic.lower().split())
        overlap = len(main_topic_words.intersection(subtopic_words))
        score += 0.1 * overlap
        important_terms = ['statistic', 'research', 'study', 'analysis', 'data', 
                           'impact', 'effect', 'cause', 'result', 'evidence']
        
        for term in important_terms:
            if term in subtopic.lower() or term in description.lower():
                score += 0.1
                break
            
        if subtopic_data.get('core', False):
            score += 0.3
            
        return min(1.0, score)