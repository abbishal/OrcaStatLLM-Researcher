
import re
import time
from typing import List, Dict, Any, Set, Optional
import logging
from urllib.parse import urlparse

logger = logging.getLogger("ContentOptimizer")

class ContentOptimizer:
    """
    Helper class for optimizing content processing during research.
    Provides methods to prioritize high-quality sources and filter redundant content.
    """
    
    def __init__(self):
        self.high_quality_domains = {
            'scholar.google.com', 'arxiv.org', 'science.org', 'nature.com', 
            'researchgate.net', 'ssrn.com', 'pubmed.ncbi.nlm.nih.gov',
            'ieee.org', 'acm.org', 'jstor.org', 'springer.com', 'wiley.com',
            'bbc.com', 'nytimes.com', 'washingtonpost.com', 'economist.com',
            'reuters.com', 'apnews.com', 'bloomberg.com', 'ft.com',
            '.edu', '.gov', '.ac.uk', '.ac.jp', '.edu.au'
        }
        self.statistics_domains = {
            'statista.com', 'census.gov', 'bls.gov', 'data.gov', 'eurostat.ec.europa.eu',
            'ons.gov.uk', 'who.int', 'worldbank.org', 'imf.org', 'oecd.org',
            'pewresearch.org', 'gallup.com', 'data.worldbank.org'
        }
        self.recency_indicators = [
            r'202[3-5]', r'last year', r'this year', r'recent', r'latest',
            r'update', r'current', r'new study', r'new research'
        ]
        self.processed_content_hashes: Set[int] = set()
        
    def prioritize_urls(self, urls: List[str]) -> List[str]:

        scored_urls = []
        
        for url in urls:
            score = 0
            domain = self._extract_domain(url)
            if domain:
                if any(domain.endswith(hq_domain) for hq_domain in self.high_quality_domains):
                    score += 10
                if any(domain.endswith(stats_domain) for stats_domain in self.statistics_domains):
                    score += 5
            if 'pdf' in url.lower():
                score += 3  # PDFs often contain research papers
            if 'research' in url.lower() or 'study' in url.lower():
                score += 2
            if 'statistics' in url.lower() or 'data' in url.lower():
                score += 2
            if 'search' in url.lower() or 'index' in url.lower() or 'list' in url.lower():
                score -= 1
                
            scored_urls.append((score, url))
        sorted_urls = [url for _, url in sorted(scored_urls, key=lambda x: x[0], reverse=True)]
        return sorted_urls
        
    def filter_redundant_content(self, content: str) -> str:
        """
        Filter out common boilerplate and redundant content to focus on the essential information
        """
        if not content:
            return ""
        content = re.sub(r'(Home|Menu|Navigation|Search|Skip to content|Back to top|Share|Print|Email)',
                        '', content)
        content = re.sub(r'(cookie|privacy|GDPR|consent|accept|notification).*?(policy|notice|banner|settings|accept)',
                        '', content, flags=re.IGNORECASE)
        content = re.sub(r'https?://\S+', '', content)
        
        return content.strip()
        
    def is_redundant(self, content: str) -> bool:
        """
        Check if content is redundant (already processed or too similar to existing content)
        """
        if not content or len(content) < 50:
            return True
        content_hash = hash(self._normalize_content(content))
        
        if content_hash in self.processed_content_hashes:
            return True
        self.processed_content_hashes.add(content_hash)
        return False
        
    def estimate_content_quality(self, content: str, title: str = "") -> float:
        """
        Estimate the quality of content on a scale of 0.0 to 1.0
        """
        if not content:
            return 0.0
            
        quality_score = 0.0
        content_length = len(content)
        if 500 <= content_length <= 10000:
            quality_score += 0.3
        elif content_length > 10000:
            quality_score += 0.2  # Penalize extremely long content that might be harder to process
        else:
            quality_score += 0.1 * (content_length / 500)  # Proportional for smaller content
        research_indicators = ['study', 'research', 'analysis', 'survey', 'found', 'according to']
        stats_indicators = ['percent', '%', 'statistics', 'data', 'figure', 'chart', 'graph', 'number']
        
        research_count = sum(1 for indicator in research_indicators 
                           if indicator in content.lower())
        stats_count = sum(1 for indicator in stats_indicators 
                        if indicator in content.lower())
                        
        quality_score += min(0.3, 0.05 * research_count)  # Up to 0.3
        quality_score += min(0.2, 0.05 * stats_count)  # Up to 0.2
        if any(re.search(indicator, content, re.IGNORECASE) for indicator in self.recency_indicators):
            quality_score += 0.2
            
        return min(1.0, quality_score)
        
    def has_sufficient_research(self, collected_data: Dict[str, Any]) -> bool:
        """
        Determine if enough research has been collected to produce a quality paper
        """
        academic_sources = 0
        if 'academic_sources' in collected_data:
            academic_sources = (
                len(collected_data.get('academic_sources', {}).get('arxiv_papers', [])) +
                len(collected_data.get('academic_sources', {}).get('doi_papers', [])) +
                len(collected_data.get('academic_sources', {}).get('academic_pdfs', []))
            )
        
        if academic_sources < 3:
            return False
        stats_sources = len(collected_data.get('academic_sources', {}).get('statistics_sources', [])) if 'academic_sources' in collected_data else 0
        if stats_sources < 2:
            return False
        research_results = collected_data.get('research_results', {})
        if len(research_results) < 3:
            return False
        content_count = 0
        for subtopic, data in research_results.items():
            if isinstance(data, dict) and 'content' in data and len(data.get('content', '')) >= 500:
                content_count += 1
        return content_count >= 3
    
    def _extract_domain(self, url: str) -> str:

        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            return domain
        except:
            return ""
            
    def _normalize_content(self, content: str) -> str:

        normalized = content.lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized.strip()
        
    def limit_content_to_essentials(self, content: str, max_length: int = 5000) -> str:
        """
        Limit content to essential parts to avoid processing too much data.
        Keeps beginning, key paragraphs with research indicators, and end.
        """
        if not content or len(content) <= max_length:
            return content
        paragraphs = re.split(r'\n\s*\n', content)
        
        if not paragraphs:
            return content[:max_length]
        essential_paragraphs = paragraphs[:2]
        scored_paragraphs = []
        middle_paragraphs = paragraphs[2:-2] if len(paragraphs) > 4 else []
        for i, para in enumerate(middle_paragraphs):
            score = 0
            research_indicators = ['study', 'research', 'analysis', 'survey', 'data', 
                                 'percent', '%', 'statistic', 'figure', 'found', 
                                 'according to', 'evidence']
                                 
            for indicator in research_indicators:
                if indicator in para.lower():
                    score += 1
            if 100 <= len(para) <= 500:
                score += 1
                
            scored_paragraphs.append((score, para))
        sorted_paragraphs = [p for _, p in sorted(scored_paragraphs, key=lambda x: x[0], reverse=True)]
        essential_paragraphs.extend(sorted_paragraphs[:5])
        if len(paragraphs) > 2:
            essential_paragraphs.extend(paragraphs[-2:])
        result = '\n\n'.join(essential_paragraphs)
        if len(result) > max_length:
            result = result[:max_length]
            
        return result

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
from .content_optimizer import ContentOptimizer  # Import the new optimizer

class OrcaStatLLMScientist:
    def __init__(self, research_id: Optional[str] = None, verbose: bool = False):
        self.max_depth = 3
        self.max_sources_per_subtopic = 8
        self.max_academic_papers = 5
        self.result_cache = {}
        self.cache_ttl = 3600  # 1 hour
        self.content_optimizer = ContentOptimizer()
        self.semaphore = asyncio.Semaphore(5)

    async def process_query_with_cache(self, query: str, buffer: 'AsyncBuffer' = None, cache_key: str = None) -> str:

        if buffer is None:
            buffer = self.AsyncBuffer(verbose=self.verbose)
        
        cache_key = cache_key or f"query_{hash(query)}"
        if cache_key in self.result_cache:
            result, timestamp = self.result_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
        
        async with self.semaphore:
            result = await self.gemini_client.query_gemini(query, buffer)
            self.result_cache[cache_key] = (result, time.time())
            return result

    async def process_query(self, query: str, buffer: 'AsyncBuffer' = None) -> str:

        if hasattr(self, 'result_cache'):  # Use caching if available
            return await self.process_query_with_cache(query, buffer)
        
        if buffer is None:
            buffer = AsyncBuffer(verbose=self.verbose)
        
        result = await self.gemini_client.query_gemini(query, buffer)
        return result

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

    async def generate_research_paper(self, topic: str) -> str:
        
        try:
            self.url_tracking = self.url_tracker.reset_tracking()
            self.result_cache = {}
            self.url_content_cache = {}
            if hasattr(self, 'content_optimizer'):
                self.content_optimizer.processed_content_hashes.clear()
            self.progress = self.progress_tracker.update_step(1, "Topic Analysis", 
                                                           "Analyzing topic type and gathering contextual information",
                                                           ["Topic classification", "News relevance analysis", "Event detection"],
                                                           0)
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 1: Analyzing topic type and generating title concurrently", high_level=True)
            analysis_task = self.topic_analyzer.analyze_topic(topic, buffer)
            title_task = asyncio.create_task(self.generate_title(topic, buffer))
            event_analysis = await analysis_task
            self.progress = self.progress_tracker.update_step(5, "Deep Research", 
                                                             "Researching and collecting data for each subtopic",
                                                             [f"Research: {subtopic_data['subtopic']}" for subtopic_data in self.subtopics_data[:3]],
                                                             0)
            if len(self.subtopics_data) > 3:
                self.progress["subtasks"].append(f"Research: {len(self.subtopics_data) - 3} more subtopics")
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
            batch_size = 2  # Process 2 subtopics at a time
            total_batches = (len(subtopics_to_research) + batch_size - 1) // batch_size
            
            for batch_idx in range(0, len(subtopics_to_research), batch_size):
                batch_num = batch_idx // batch_size + 1
                buffer.add_log(f"Processing subtopic batch {batch_num}/{total_batches}", high_level=True)
                
                batch_tasks = []
                for i in range(batch_idx, min(batch_idx + batch_size, len(subtopics_to_research))):
                    subtopic_data = subtopics_to_research[i]
                    buffer.add_log(f"Starting research for subtopic {i+1}/{len(subtopics_to_research)}: {subtopic_data['subtopic']}", high_level=True)
                    task = asyncio.create_task(
                        self.subtopic_researcher.research_subtopic(topic, subtopic_data, buffer, self.combined_insights, self.progress)
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
                            completion_percentage = (i - 2) / (len(subtopics_to_research) - 3)
                            self.progress["completed_subtasks"] = 3 + completion_percentage
                        self._update_progress_state(buffer)
                        if hasattr(self, 'content_optimizer') and len(section_results) >= 3:
                            if self.content_optimizer.has_sufficient_research(self.research_data):
                                buffer.add_log("Sufficient research gathered for quality paper. Proceeding to content generation.", high_level=True)
                                break
                        
                    except Exception as e:
                        buffer.add_log(f"Error researching subtopic {i+1}: {str(e)}", high_level=True)
                        self.log_exception(e, f"Error researching subtopic {i+1}", buffer, self.research_data, self.save_research_data)
                        section = {"subtopic": subtopics_to_research[i]["subtopic"], 
                                  "content": f"Limited information available on this subtopic."}
                        section_results.append(section)
                        self.research_data["research_results"][section["subtopic"]] = section
                        self.save_research_data()
            
        except Exception as e:
            buffer.add_log(f"Error in research paper generation: {str(e)}", high_level=True)
            self.log_exception(e, "Error in research paper generation", buffer, self.research_data, self.save_research_data)
            return ""

    def _estimate_subtopic_importance(self, subtopic_data: Dict[str, Any], main_topic: str) -> float:
        """
        Estimate the importance of a subtopic for prioritization.
        Returns a score from 0.0 to 1.0
        """
        subtopic = subtopic_data.get('subtopic', '')
        description = subtopic_data.get('description', '')
        
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
