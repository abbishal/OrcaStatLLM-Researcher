import re
from typing import Dict, List, Any, Optional
from modules.utils.async_buffer import AsyncBuffer

class LiteratureReviewEnhancer:
    
    async def enhance_literature_review(self, 
                                       topic: str, 
                                       arxiv_insights: Dict, 
                                       buffer: AsyncBuffer,
                                       query_func) -> Dict:

        if not arxiv_insights or not arxiv_insights.get("insights"):
            buffer.add_log("No literature review content to enhance", high_level=True)
            return arxiv_insights
        
        buffer.add_log("Enhancing literature review to better align with paper topic", high_level=True)
        current_insights = arxiv_insights.get("insights", "")
        papers = arxiv_insights.get("papers", [])
        
        if len(papers) == 0:
            buffer.add_log("No academic papers available for literature review enhancement", high_level=True)
            return arxiv_insights
        paper_titles = "\n".join([f"- {p.get('title')} ({p.get('published', 'n.d.')})" for p in papers[:3]])
        
        prompt = f"""
You are an academic research assistant improving a literature review section for a paper on "{topic}".

Current literature review content:
{current_insights}

Available academic papers:
{paper_titles}

Enhance the literature review to:
1. Directly connect to the main paper topic: "{topic}"
2. Reference specific papers from the list above
3. Analyze how existing literature informs the current research
4. Identify gaps in the literature that this paper addresses
5. Use proper academic language and citation style
6. Maintain a length of 350-450 words

Please rewrite the literature review section to better align with the paper's focus.
"""
        
        try:
            enhanced_insights = await query_func(prompt, buffer)
            arxiv_insights["insights"] = enhanced_insights
            buffer.add_log("Successfully enhanced literature review to align with paper topic", high_level=True)
            
            return arxiv_insights
            
        except Exception as e:
            buffer.add_log(f"Error enhancing literature review: {str(e)}", high_level=True)
            return arxiv_insights
    
    async def validate_citations(self, 
                               arxiv_insights: Dict, 
                               buffer: AsyncBuffer,
                               query_func) -> List[str]:
        """
        Validate and potentially fix citations in the literature review.
        
        Args:
            arxiv_insights: Dictionary with literature info
            buffer: AsyncBuffer for logging
            query_func: Function to query LLM
            
        Returns:
            List of corrected citations
        """
        if not arxiv_insights or not arxiv_insights.get("citations"):
            return []
        
        current_citations = arxiv_insights.get("citations", [])
        
        if len(current_citations) == 0:
            return []
            
        buffer.add_log("Validating literature review citations", high_level=True)
        citations_text = "\n".join([f"- {c}" for c in current_citations])
        
        prompt = f"""
You are an academic citation specialist. Review these academic paper citations and ensure they follow proper APA format:

{citations_text}

For each citation, verify:
1. Author names are correctly formatted (Last name, First initial.)
2. Year is in parentheses
3. Title is properly capitalized (only first word and proper nouns)
4. Publication source is italicized (use *Journal Name* format in markdown)
5. DOI or URL is properly formatted if present

Return the corrected list of citations, each on a new line.
"""
        
        try:
            corrected_citations_text = await query_func(prompt, buffer)
            corrected_citations = []
            for line in corrected_citations_text.strip().split('\n'):
                if line.strip() and not line.startswith('#') and not line.startswith('-'):
                    corrected_citations.append(line.strip())
                elif line.strip().startswith('- '):
                    corrected_citations.append(line.strip()[2:])
            
            buffer.add_log(f"Validated {len(corrected_citations)} literature citations", high_level=True)
            return corrected_citations
            
        except Exception as e:
            buffer.add_log(f"Error validating citations: {str(e)}", high_level=True)
            return current_citations
