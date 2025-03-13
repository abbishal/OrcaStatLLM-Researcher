import re
import datetime
from typing import List, Dict, Optional, Union
import uuid

class SourceReference:

    
    def __init__(self, title: str, url: str, authors: List[str] = None, 
                 publication_date: str = None, source_type: str = "web",
                 publisher: str = None, journal: str = None, doi: str = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.url = url
        self.authors = authors or []
        self.publication_date = publication_date
        self.source_type = source_type  # web, arxiv, journal, book, etc.
        self.publisher = publisher
        self.journal = journal
        self.doi = doi
        self.citation_number = None
        self.relevance_score = 0.5
        self.quality_score = 0.5
        self.recency_score = 0.5
        self.authority_score = 0.5

    def calculate_scores(self):

        if self.publication_date:
            try:
                pub_date = None
                if isinstance(self.publication_date, str):
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%d %B %Y", "%Y"):
                        try:
                            pub_date = datetime.datetime.strptime(self.publication_date, fmt).date()
                            break
                        except ValueError:
                            continue
                
                if pub_date:
                    today = datetime.date.today()
                    days_old = (today - pub_date).days
                    if days_old < 365:  # Less than a year old
                        self.recency_score = 0.9
                    elif days_old < 365 * 3:  # Less than 3 years old
                        self.recency_score = 0.7
                    elif days_old < 365 * 5:  # Less than 5 years old
                        self.recency_score = 0.5
                    else:
                        self.recency_score = 0.3
            except Exception:
                pass
        if self.source_type == "arxiv":
            self.authority_score = 0.8
        elif self.source_type == "journal" and self.journal:
            self.authority_score = 0.9
        elif self.source_type == "wikipedia":
            self.authority_score = 0.6
        elif "github" in self.url or "edu" in self.url:
            self.authority_score = 0.7
        self.quality_score = (self.relevance_score + self.recency_score + self.authority_score) / 3

    def to_dict(self) -> Dict:

        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "authors": self.authors,
            "publication_date": self.publication_date,
            "source_type": self.source_type,
            "publisher": self.publisher,
            "journal": self.journal,
            "doi": self.doi,
            "citation_number": self.citation_number,
            "relevance_score": self.relevance_score,
            "quality_score": self.quality_score,
            "recency_score": self.recency_score,
            "authority_score": self.authority_score
        }

    def format_citation(self, style="apa") -> str:

        if style == "apa":
            return self._format_apa()
        elif style == "mla":
            return self._format_mla()
        elif style == "chicago":
            return self._format_chicago()
        elif style == "harvard":
            return self._format_harvard()
        elif style == "ieee":
            return self._format_ieee()
        else:
            return self._format_apa()

    def _format_apa(self) -> str:

        citation = ""
        if self.authors:
            if len(self.authors) == 1:
                citation += f"{self.authors[0]}. "
            elif len(self.authors) == 2:
                citation += f"{self.authors[0]} & {self.authors[1]}. "
            elif len(self.authors) > 2:
                citation += f"{self.authors[0]} et al. "
        if self.publication_date:
            citation += f"({self.publication_date}). "
        citation += f"{self.title}. "
        if self.source_type == "journal" and self.journal:
            citation += f"{self.journal}"
            if self.doi:
                citation += f". https://doi.org/{self.doi}"
        elif self.source_type == "arxiv":
            citation += f"arXiv preprint arXiv:{self.url.split('/')[-1]}"
        elif self.source_type == "book" and self.publisher:
            citation += f"{self.publisher}"
        else:
            citation += f"Retrieved from {self.url}"
        
        return citation

    def _format_mla(self) -> str:

        citation = ""
        if self.authors:
            if len(self.authors) == 1:
                citation += f"{self.authors[0]}. "
            elif len(self.authors) == 2:
                citation += f"{self.authors[0]} and {self.authors[1]}. "
            elif len(self.authors) > 2:
                citation += f"{self.authors[0]} et al. "
        citation += f"\"{self.title}.\" "
        if self.source_type == "journal" and self.journal:
            citation += f"{self.journal}"
            if self.publication_date:
                citation += f", {self.publication_date}"
        elif self.source_type == "arxiv":
            citation += f"arXiv"
            if self.publication_date:
                citation += f", {self.publication_date}"
        elif self.source_type == "book" and self.publisher:
            citation += f"{self.publisher}"
            if self.publication_date:
                citation += f", {self.publication_date}"
        else:
            citation += f"{self.url}"
            if self.publication_date:
                citation += f", {self.publication_date}"
        
        return citation

    def _format_chicago(self) -> str:

        return self._format_apa()  # Simplified for now

    def _format_harvard(self) -> str:

        return self._format_apa()  # Simplified for now

    def _format_ieee(self) -> str:

        if self.citation_number:
            return f"[{self.citation_number}] "
        
        citation = ""
        if self.authors:
            if len(self.authors) == 1:
                citation += f"{self.authors[0]}, "
            elif len(self.authors) > 1:
                for i, author in enumerate(self.authors[:-1]):
                    citation += f"{author}, "
                citation += f"and {self.authors[-1]}, "
        citation += f"\"{self.title},\" "
        if self.source_type == "journal" and self.journal:
            citation += f"{self.journal}"
            if self.publication_date:
                citation += f", {self.publication_date}"
        elif self.source_type == "arxiv":
            citation += f"arXiv preprint arXiv:{self.url.split('/')[-1]}"
        elif self.source_type == "book" and self.publisher:
            citation += f"{self.publisher}"
            if self.publication_date:
                citation += f", {self.publication_date}"
        else:
            citation += f"Retrieved from {self.url}"
            if self.publication_date:
                citation += f", {self.publication_date}"
        
        return citation

class Citation:

    
    def __init__(self, style="apa"):
        self.references: Dict[str, SourceReference] = {}  # url -> SourceReference
        self.reference_map: Dict[str, str] = {}  # reference_id -> url
        self.style = style
        self.citation_counter = 1

    def add_reference(self, reference: SourceReference) -> str:

        if reference.url not in self.references:
            reference.citation_number = self.citation_counter
            self.citation_counter += 1
            self.references[reference.url] = reference
            self.reference_map[reference.id] = reference.url
        return reference.id

    def get_reference(self, ref_id: str) -> Optional[SourceReference]:

        if ref_id in self.reference_map:
            url = self.reference_map[ref_id]
            return self.references.get(url)
        return None

    def get_reference_by_url(self, url: str) -> Optional[SourceReference]:

        return self.references.get(url)

    def generate_citation(self, ref_id: str) -> str:

        if ref_id in self.reference_map:
            url = self.reference_map[ref_id]
            ref = self.references.get(url)
            if ref and ref.citation_number:
                if self.style == "ieee":
                    return f"[{ref.citation_number}]"
                else:
                    return f"({ref.citation_number})"
        return "(citation error)"

    def extract_citations_from_text(self, text: str) -> List[str]:

        citation_patterns = [
            r'\[(\d+)\]',  # [1], [2], etc
            r'\((\d+)\)',  # (1), (2), etc
            r'(\[\w+\d*\])'  # [Author2023], etc
        ]
        citations = []
        for pattern in citation_patterns:
            citations.extend(re.findall(pattern, text))
        return citations

    def generate_references_section(self) -> str:

        if not self.references:
            return "No references found."
        sorted_refs = sorted(
            self.references.values(), 
            key=lambda r: r.citation_number if r.citation_number is not None else 999
        )
        
        references_text = ""
        for ref in sorted_refs:
            ref_num = f"[{ref.citation_number}] " if ref.citation_number else ""
            formatted_citation = ref.format_citation(self.style)
            references_text += f"{ref_num}{formatted_citation}\n\n"
        
        return references_text
