import json
import datetime
from pathlib import Path
from typing import Dict

class ResearchDataManager:
    def __init__(self, research_data_file: Path):
        self.research_data_file = research_data_file

    def load_research_data(self) -> Dict:
        if self.research_data_file.exists():
            with open(self.research_data_file, 'r') as f:
                return json.load(f)
        return {
            "topic": "",
            "title": "",
            "subtopics": [],
            "research_results": {},
            "created_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
            "status": "initialized",
            "images": {},
            "tables": [],
            "figures": {},
            "references": {},
            "url_tracking": {
                "total_urls_scraped": 0,
                "web_page_count": 0,
                "wikipedia_count": 0,
                "news_count": 0,
                "arxiv_count": 0,
                "academic_pdf_count": 0,
                "doi_papers_count": 0,
                "stats_sources_count": 0,
                "failed_scrapes": 0
            },
            "academic_sources": {
                "arxiv_papers": [],
                "doi_papers": [],
                "academic_pdfs": [],
                "statistics_sources": []
            }
        }

    def save_research_data(self, research_data: Dict):

        def json_serialize_handler(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            if isinstance(obj, datetime.date):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        with open(self.research_data_file, 'w') as f:
            json.dump(research_data, f, indent=2, default=json_serialize_handler)

