import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import datetime

class ArticleStorage:

    
    def __init__(self, storage_dir: Optional[Path] = None):

        if storage_dir is None:
            self.storage_dir = Path.home() / ".orcallm" / "articles"
        else:
            self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "article_index.json"
        if not self.index_path.exists():
            with open(self.index_path, 'w') as f:
                json.dump({
                    "articles": {},
                    "last_updated": datetime.datetime.now().isoformat()
                }, f, indent=2)
    
    def store_article(self, url: str, title: str, content: str, 
                     source_type: str, metadata: Optional[Dict] = None) -> str:
        article_id = self._hash_url(url)
        article_data = {
            "id": article_id,
            "url": url,
            "title": title,
            "source_type": source_type,
            "timestamp": time.time(),
            "date_added": datetime.datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        content_path = self.storage_dir / f"{article_id}.txt"
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        index = self._load_index()
        index["articles"][article_id] = article_data
        index["last_updated"] = datetime.datetime.now().isoformat()
        self._save_index(index)
        
        return article_id
    
    def get_article_content(self, article_id: str) -> Optional[str]:
        content_path = self.storage_dir / f"{article_id}.txt"
        if content_path.exists():
            with open(content_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def get_article_metadata(self, article_id: str) -> Optional[Dict]:
        index = self._load_index()
        return index["articles"].get(article_id)
    
    def get_article_by_url(self, url: str) -> Optional[Dict]:
        article_id = self._hash_url(url)
        return self.get_article_metadata(article_id)
    
    def has_article(self, url: str) -> bool:
        article_id = self._hash_url(url)
        index = self._load_index()
        return article_id in index["articles"]
    
    def get_articles_by_type(self, source_type: str) -> List[Dict]:
        index = self._load_index()
        return [article for article in index["articles"].values() 
                if article["source_type"] == source_type]
    
    def get_recent_articles(self, n: int = 10) -> List[Dict]:
        index = self._load_index()
        sorted_articles = sorted(
            index["articles"].values(),
            key=lambda x: x["timestamp"],
            reverse=True  # Most recent first
        )
        return sorted_articles[:n]
    
    def add_summary_to_article(self, article_id: str, summary: str) -> bool:
        index = self._load_index()
        if article_id not in index["articles"]:
            return False
        index["articles"][article_id]["metadata"]["summary"] = summary
        index["articles"][article_id]["metadata"]["summary_date"] = datetime.datetime.now().isoformat()
        self._save_index(index)
        
        return True
    
    def _hash_url(self, url: str) -> str:

        return hashlib.md5(url.encode()).hexdigest()
    
    def _load_index(self) -> Dict:

        with open(self.index_path, 'r') as f:
            return json.load(f)
    
    def _save_index(self, index: Dict) -> None:

        with open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2)
    
    def cleanup_old_articles(self, days: int = 30) -> int:
        cutoff_time = time.time() - (days * 86400)  # 86400 seconds in a day
        
        index = self._load_index()
        articles_to_remove = []
        for article_id, article in index["articles"].items():
            if article["timestamp"] < cutoff_time:
                articles_to_remove.append(article_id)
        for article_id in articles_to_remove:
            content_path = self.storage_dir / f"{article_id}.txt"
            if content_path.exists():
                os.remove(content_path)
            del index["articles"][article_id]
        if articles_to_remove:
            index["last_updated"] = datetime.datetime.now().isoformat()
            self._save_index(index)
        
        return len(articles_to_remove)
