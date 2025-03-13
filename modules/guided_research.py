import asyncio
import logging
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from modules.researcher import OrcaStatLLMScientist
from modules.utils.async_buffer import AsyncBuffer
from modules.document.markdown_generator import MarkdownGenerator
from modules.document.pdf_converter import PDFConverter  

logger = logging.getLogger("GuidedResearch")

class GuidedResearchAssistant:
    
    def __init__(self, research_id: Optional[str] = None, verbose: bool = False):
        self.core_researcher = OrcaStatLLMScientist(research_id=research_id, verbose=verbose)
        self.verbose = verbose
        self.research_id = self.core_researcher.research_id
        self.research_dir = self.core_researcher.research_dir
        self.guidance_dir = self.research_dir / "guidance"
        os.makedirs(self.guidance_dir, exist_ok=True)
        self.goals = []
        self.topic = ""
        self.additional_context = ""
        self.progress = {
            "current_step": 0,
            "max_steps": 7,  
            "step_name": "Initializing",
            "step_details": "Setting up guided research environment",
            "subtasks": [],
            "completed_subtasks": 0
        }

    async def generate_research_guidance(self, topic: str, goals: List[str], additional_context: str = "") -> str:
        buffer = AsyncBuffer(verbose=self.verbose)
        self.topic = topic
        self.goals = goals
        self.additional_context = additional_context
        
        buffer.add_log(f"Starting guided research assistance for: {topic}", high_level=True)
        buffer.add_log(f"Goals: {', '.join(goals)}", high_level=True)
        
        try:
            self.progress["current_step"] = 1
            self.progress["step_name"] = "Topic Analysis"
            self.progress["step_details"] = "Analyzing topic and providing refinement suggestions"
            self.progress["subtasks"] = ["Topic classification", "Key concepts identification", "Research question development"]
            self.progress["completed_subtasks"] = 0
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 1: Analyzing research topic", high_level=True)
            topic_analysis = await self._analyze_topic(topic, buffer)
            
            self.progress["completed_subtasks"] = len(self.progress["subtasks"])
            self._update_progress_state(buffer)
            self.progress["current_step"] = 2
            self.progress["step_name"] = "Research Question Development"
            self.progress["step_details"] = "Formulating effective research questions"
            self.progress["subtasks"] = ["Primary question development", "Supporting questions", "Hypothesis formulation"]
            self.progress["completed_subtasks"] = 0
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 2: Formulating research questions", high_level=True)
            research_questions = await self._formulate_research_questions(topic, topic_analysis, buffer)
            
            self.progress["completed_subtasks"] = len(self.progress["subtasks"])
            self._update_progress_state(buffer)
            self.progress["current_step"] = 3
            self.progress["step_name"] = "Academic Resources"
            self.progress["step_details"] = "Finding relevant academic sources and organizing literature review"
            self.progress["subtasks"] = ["Academic source search", "Paper evaluation", "Literature organization", "Citation guidance"]
            self.progress["completed_subtasks"] = 0
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 3: Identifying academic sources and structuring literature review", high_level=True)
            academic_sources, literature_review_structure = await self._research_academic_sources(topic, buffer)
            
            self.progress["completed_subtasks"] = len(self.progress["subtasks"])
            self._update_progress_state(buffer)
            self.progress["current_step"] = 4
            self.progress["step_name"] = "Methodology Guidance"
            self.progress["step_details"] = "Suggesting appropriate research methodologies"
            self.progress["subtasks"] = ["Methodology assessment", "Research design suggestions", "Data collection approaches", "Analytical frameworks"]
            self.progress["completed_subtasks"] = 0
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 4: Suggesting appropriate research methodologies", high_level=True)
            methodology_guidance = await self._suggest_methodologies(topic, buffer)
            
            self.progress["completed_subtasks"] = len(self.progress["subtasks"])
            self._update_progress_state(buffer)

            self.progress["current_step"] = 5
            self.progress["step_name"] = "Paper Structure"
            self.progress["step_details"] = "Creating effective paper structure and outline"
            self.progress["subtasks"] = ["Overall structure development", "Section planning", "Content organization", "Flow optimization"]
            self.progress["completed_subtasks"] = 0
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 5: Developing paper structure and organization", high_level=True)
            paper_structure = await self._develop_structure(topic, research_questions, buffer)
            
            self.progress["completed_subtasks"] = len(self.progress["subtasks"])
            self._update_progress_state(buffer)

            data_analysis_guidance = None
            if "data_analysis" in goals:
                self.progress["current_step"] = 6
                self.progress["step_name"] = "Data Analysis Planning"
                self.progress["step_details"] = "Providing guidance on data analysis approaches"
                self.progress["subtasks"] = ["Data type assessment", "Analysis method suggestions", "Visual representation ideas", "Statistical approaches"]
                self.progress["completed_subtasks"] = 0
                self._update_progress_state(buffer)
                
                buffer.add_log("Step 6: Providing data analysis guidance", high_level=True)
                data_analysis_guidance = await self._provide_data_analysis_guidance(topic, buffer)
                
                self.progress["completed_subtasks"] = len(self.progress["subtasks"])
                self._update_progress_state(buffer)
            
            self.progress["current_step"] = 7
            self.progress["step_name"] = "Finalizing Guidance"
            self.progress["step_details"] = "Creating comprehensive research guidance document"
            self.progress["subtasks"] = ["Compiling information", "Formatting document", "Adding resources", "Final review"]
            self.progress["completed_subtasks"] = 0
            self._update_progress_state(buffer)
            
            buffer.add_log("Step 7: Generating comprehensive guidance document", high_level=True)
            markdown_file = await self._compile_guidance_document(
                topic=topic,
                topic_analysis=topic_analysis,
                research_questions=research_questions,
                academic_sources=academic_sources,
                literature_review_structure=literature_review_structure,
                methodology_guidance=methodology_guidance,
                paper_structure=paper_structure,
                data_analysis_guidance=data_analysis_guidance,
                buffer=buffer
            )
            
            self.progress["completed_subtasks"] = len(self.progress["subtasks"])
            self.progress["step_name"] = "Completed"
            self.progress["step_details"] = "Research guidance document is ready"
            self._update_progress_state(buffer)
            
            buffer.add_log("Research guidance document generated successfully!", high_level=True)
            
            return markdown_file
            
        except Exception as e:
            buffer.add_log(f"Error generating research guidance: {str(e)}", high_level=True)
            error_file = self.guidance_dir / "error_guidance.md"
            with open(error_file, 'w') as f:
                f.write(f"# Error in Research Guidance Generation\n\n")
                f.write(f"**Topic:** {topic}\n\n")
                f.write(f"**Error Message:** {str(e)}\n\n")
                f.write("## Partial Results\n\n")
                f.write("We apologize for the error. Here is what we were able to analyze:\n\n")
                if hasattr(self, 'topic_analysis') and self.topic_analysis:
                    f.write("### Topic Analysis\n\n")
                    f.write(f"{self.topic_analysis}\n\n")
        
                f.write("### Process Log\n\n")
                logs = buffer.get_logs()
                for log in logs[-20:]: 
                    f.write(f"- {log.get('message', '')}\n")
                    
            return str(error_file)
            
    def _update_progress_state(self, buffer=None):
        if buffer:
            buffer.add_log(f"Progress: {self.progress['current_step']}/{self.progress['max_steps']} - {self.progress['step_name']}", high_level=True)
        self.core_researcher.progress = self.progress
        self.core_researcher.save_research_data()
        
    async def _analyze_topic(self, topic: str, buffer: AsyncBuffer) -> Dict:
        buffer.add_log("Analyzing research topic...", high_level=True)
        
        prompt = f"""
You are an expert research advisor helping a researcher refine their topic.
Analyze this research topic: "{topic}"

Provide a detailed analysis with:
1. Topic classification (field, subfield, specific area)
2. Key concepts and terminology essential for this research
3. Current relevance and significance of this topic in its field
4. Potential scope refinements (broader or narrower approaches)
5. Cross-disciplinary connections where relevant
6. Identify any ambiguities or areas that need clarification

Format your response as detailed paragraphs with clear section headings.
"""
        
        topic_analysis = await self.core_researcher.process_query(prompt, buffer)
        buffer.add_log("Topic analysis completed", high_level=True)
        self.topic_analysis = topic_analysis
        
        return {
            "analysis": topic_analysis,
            "topic": topic
        }
    
    async def _formulate_research_questions(self, topic: str, topic_analysis: Dict, buffer: AsyncBuffer) -> Dict:
        buffer.add_log("Formulating research questions...", high_level=True)
        
        prompt = f"""
You are an expert research methodology advisor helping a researcher develop effective research questions.
Based on this research topic: "{topic}"

And this topic analysis:
{topic_analysis['analysis'][:1000]}...

Develop a comprehensive set of research questions:
1. One primary research question that is specific, feasible, and significant
2. 3-4 supporting sub-questions that help address different aspects of the primary question
3. 1-2 potential hypotheses that could be tested
4. Explain the rationale behind each question and its significance

For each question, explain:
- Why it's important to the overall research
- What methodology might best address it
- Potential challenges in answering it

Format your response with clear headings and numbered questions.
"""
        
        questions = await self.core_researcher.process_query(prompt, buffer)
        buffer.add_log("Research questions formulated", high_level=True)
        
        return {
            "questions": questions,
            "topic": topic
        }
    
    async def _research_academic_sources(self, topic: str, buffer: AsyncBuffer) -> tuple:
        buffer.add_log("Researching academic sources...", high_level=True)
        try:
            if not hasattr(self.core_researcher.academic_researcher, 'web_scraper') or not self.core_researcher.academic_researcher.web_scraper:
                self.core_researcher.academic_researcher.web_scraper = self.core_researcher.web_scraper
            buffer.add_log("Searching for arXiv papers", high_level=True)
            try:
                arxiv_insights = await self.core_researcher.arxiv_researcher.research_arxiv_papers(topic, buffer, self.core_researcher.academic_sources)
            except Exception as e:
                logging.error(f"Error fetching arxiv papers: {str(e)}")
                arxiv_insights = []
            
            buffer.add_log("Searching for academic PDFs using specialized queries", high_level=True)
            try:
                academic_insights = await self.core_researcher.academic_researcher.research_academic_papers_with_dorks(topic, buffer, self.core_researcher.academic_sources)
            except Exception as e:
                logging.error(f"Error fetching academic papers with dorks: {str(e)}")
                buffer.add_log(f"Error in academic papers research with dorks: {str(e)}", high_level=True)
                academic_insights = []
            
            buffer.add_log("Searching for papers with DOIs", high_level=True)
            try:
                doi_papers = await self.core_researcher.doi_researcher.research_doi_papers(topic, buffer, self.core_researcher.academic_sources)
            except Exception as e:
                logging.error(f"Error fetching DOI papers: {str(e)}")
                doi_papers = []
            buffer.add_log("Combining academic insights", high_level=True)
            combined_sources = self.core_researcher.academic_researcher.combine_academic_insights(
                arxiv_insights, 
                academic_insights, 
                {}, 
                doi_papers,
                buffer
            )
            
            academic_sources = {
                "arxiv_papers": self.core_researcher.academic_sources.get('arxiv_papers', [])[:5],
                "doi_papers": self.core_researcher.academic_sources.get('doi_papers', [])[:5],
                "academic_pdfs": self.core_researcher.academic_sources.get('academic_pdfs', [])[:5],
                "citation_summaries": combined_sources.get('paper_summaries', [])[:10]
            }
            
            self.academic_sources = academic_sources
            
        except Exception as e:
            buffer.add_log(f"Error researching academic sources: {str(e)}", high_level=True)
            academic_sources = {
                "arxiv_papers": [],
                "doi_papers": [],
                "academic_pdfs": [],
                "citation_summaries": []
            }
        buffer.add_log("Developing literature review structure...", high_level=True)
        paper_count = len(academic_sources.get("arxiv_papers", [])) + \
                     len(academic_sources.get("doi_papers", [])) + \
                     len(academic_sources.get("academic_pdfs", []))
        
        prompt = f"""
You are an expert academic advisor helping a researcher structure their literature review.
The research topic is: "{topic}"

I have found approximately {paper_count} relevant academic sources.

Provide detailed guidance on:
1. How to structure a literature review for this specific topic
2. Suggested categories or themes for organizing the literature
3. Approaches for synthesizing contradictory findings
4. Identifying research gaps based on the literature
5. Effective methods for critiquing and evaluating relevant studies
6. Tips for integrating theoretical frameworks from the literature

Your guidance should be specific to this topic, not just generic literature review advice.
Include examples of how specific aspects of {topic} could be organized in the literature review.
Format your response with clear section headings and actionable guidance.
"""
        
        literature_review_structure = await self.core_researcher.process_query(prompt, buffer)
        buffer.add_log("Literature review structure completed", high_level=True)
        
        return academic_sources, literature_review_structure
        
    async def _suggest_methodologies(self, topic: str, buffer: AsyncBuffer) -> str:
        buffer.add_log("Generating methodology suggestions...", high_level=True)
        
        prompt = f"""
You are an expert research methodology advisor helping a researcher design their study.
The research topic is: "{topic}"

Provide comprehensive methodology guidance including:
1. 2-3 potentially appropriate research designs for this topic (e.g., experimental, case study, survey, mixed methods)
2. For each design:
   - Why it's suitable for this specific research topic
   - Data collection methods that align with this design
   - Potential sampling approaches
   - Analysis techniques that would be appropriate
   - Limitations and how to address them
3. Ethical considerations specific to this research topic
4. Validity and reliability strategies relevant to the proposed methods
5. Practical implementation considerations (timeline, resources)

Focus on methodologies that are feasible for academic research and appropriate for this specific topic.
Your guidance should reflect current best practices in the field related to this topic.
Format with clear headings and practical, actionable advice.
"""
        
        methodologies = await self.core_researcher.process_query(prompt, buffer)
        buffer.add_log("Methodology suggestions completed", high_level=True)
        
        return methodologies
    
    async def _develop_structure(self, topic: str, research_questions: Dict, buffer: AsyncBuffer) -> str:
        buffer.add_log("Developing paper structure...", high_level=True)
        
        prompt = f"""
You are an expert academic writing advisor helping a researcher structure their research paper.
The research topic is: "{topic}"

The primary research question is included in:
{research_questions['questions'][:500]}...

Provide detailed guidance on structuring an effective academic paper, including:
1. A complete outline with all major sections and subsections
2. Specific content recommendations for each section
3. Approximate word count/length for each section
4. Logical flow and transitions between sections
5. Placement of research questions, theoretical framework, and hypotheses
6. Strategies for maintaining coherence throughout the paper

For each major section (e.g., Introduction, Literature Review, Methodology), provide:
- Key components that must be included
- Common pitfalls to avoid
- Tips for effective writing specific to that section

Your guidance should result in a comprehensive blueprint that the researcher can follow to create a well-structured paper.
Format with clear headings, bullet points for key elements, and specific guidance tailored to this research topic.
"""
        
        structure = await self.core_researcher.process_query(prompt, buffer)
        buffer.add_log("Paper structure completed", high_level=True)
        
        return structure
    
    async def _provide_data_analysis_guidance(self, topic: str, buffer: AsyncBuffer) -> str:
        buffer.add_log("Generating data analysis guidance...", high_level=True)
        
        prompt = f"""
You are an expert data analysis advisor helping a researcher plan their data analysis strategy.
The research topic is: "{topic}"

Provide comprehensive guidance on data analysis approaches, including:
1. Potential types of data that could be collected for this research topic
2. Appropriate statistical or qualitative analysis methods for each data type
3. Suggestions for data visualization and presentation
4. Software tools and resources that would be helpful for this analysis
5. Strategies for interpreting results in the context of the research questions
6. Methods for ensuring rigor and validity in the analysis
7. Examples of tables, charts, or figures that could effectively present findings

For quantitative approaches:
- Suggest specific statistical tests appropriate for this topic
- Explain how to interpret the results of these tests
- Discuss sample size considerations

For qualitative approaches:
- Suggest coding and theme development strategies
- Discuss approaches to ensuring trustworthiness
- Explain how to effectively present qualitative findings

Your guidance should help the researcher make informed decisions about their analysis approach.
Format with clear headings, concrete examples, and actionable recommendations specific to this research topic.
"""
        
        data_analysis = await self.core_researcher.process_query(prompt, buffer)
        buffer.add_log("Data analysis guidance completed", high_level=True)
        
        return data_analysis
    
    async def _compile_guidance_document(self, topic: str, topic_analysis: Dict, 
                                       research_questions: Dict, academic_sources: Dict,
                                       literature_review_structure: str, methodology_guidance: str,
                                       paper_structure: str, data_analysis_guidance: str,
                                       buffer: AsyncBuffer) -> str:
        buffer.add_log("Compiling guidance document...", high_level=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        safe_topic = topic.replace(" ", "_")[:30]
        filename = f"{timestamp}_research_guidance_{safe_topic}.md"
        file_path = self.guidance_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Research Guidance: {topic}\n\n")
            f.write(f"*Generated by OrcaStatLLM Research Assistant on {datetime.now().strftime('%B %d, %Y')}*\n\n")
            
            f.write("## Table of Contents\n\n")
            f.write("1. [Topic Analysis & Refinement](#topic-analysis--refinement)\n")
            f.write("2. [Research Questions & Hypotheses](#research-questions--hypotheses)\n")
            f.write("3. [Academic Sources](#academic-sources)\n")
            f.write("4. [Literature Review Structure](#literature-review-structure)\n")
            f.write("5. [Research Methodology](#research-methodology)\n")
            f.write("6. [Paper Structure & Organization](#paper-structure--organization)\n")
            if data_analysis_guidance:
                f.write("7. [Data Analysis Guidance](#data-analysis-guidance)\n")
            f.write("8. [Next Steps & Resources](#next-steps--resources)\n\n")
            f.write("## Topic Analysis & Refinement\n\n")
            f.write(topic_analysis["analysis"])
            f.write("\n\n")
            f.write("## Research Questions & Hypotheses\n\n")
            f.write(research_questions["questions"])
            f.write("\n\n")
            f.write("## Academic Sources\n\n")
            f.write("The following academic sources were identified as relevant to your topic. These can serve as a starting point for your literature review.\n\n")
            if academic_sources.get("arxiv_papers"):
                f.write("### ArXiv Papers\n\n")
                for i, paper in enumerate(academic_sources["arxiv_papers"], 1):
                    f.write(f"{i}. **{paper.get('title', 'Untitled')}**  \n")
                    f.write(f"   Authors: {', '.join(paper.get('authors', ['Unknown']))}\n  ")
                    f.write(f"   Published: {paper.get('published', 'Unknown date')}  \n")
                    f.write(f"   URL: [{paper.get('id', 'Link')}](https://arxiv.org/abs/{paper.get('id', '')})\n\n")
                f.write("\n")
            
            if academic_sources.get("doi_papers"):
                f.write("### DOI Papers\n\n")
                for i, paper in enumerate(academic_sources["doi_papers"], 1):
                    f.write(f"{i}. **{paper.get('Title', 'Untitled')}**  \n")
                    authors = paper.get('Authors', [])
                    if isinstance(authors, list):
                        f.write(f"   Authors: {', '.join(authors)}  \n")
                    f.write(f"   Published: {paper.get('Publication Date', 'Unknown date')}  \n")
                    f.write(f"   Journal: {paper.get('Journal', 'Unknown journal')}  \n")
                    f.write(f"   DOI: {paper.get('DOI', 'Unknown DOI')}  \n")
                    if paper.get('Read Link'):
                        f.write(f"   [Access Paper]({paper.get('Read Link')})\n\n")
                f.write("\n")

            if academic_sources.get("academic_pdfs"):
                f.write("### Other Academic Sources\n\n")
                for i, paper in enumerate(academic_sources["academic_pdfs"], 1):
                    f.write(f"{i}. **{paper.get('title', 'Untitled')}**  \n")
                    f.write(f"   Source: {paper.get('source', 'Unknown source')}  \n")
                    if paper.get('url'):
                        f.write(f"   [Access Paper]({paper.get('url')})\n\n")
                f.write("\n")
            
            if academic_sources.get("citation_summaries"):
                f.write("### Key Paper Summaries\n\n")
                for i, summary in enumerate(academic_sources["citation_summaries"], 1):
                    f.write(f"{i}. **{summary.get('title', 'Untitled')}**  \n")
                    f.write(f"{summary.get('summary', 'No summary available')}\n\n")
                f.write("\n")
            
            f.write("## Literature Review Structure\n\n")
            f.write(literature_review_structure)
            f.write("\n\n")
            
            f.write("## Research Methodology\n\n")
            f.write(methodology_guidance)
            f.write("\n\n")
            
            f.write("## Paper Structure & Organization\n\n")
            f.write(paper_structure)
            f.write("\n\n")
            
            if data_analysis_guidance:
                f.write("## Data Analysis Guidance\n\n")
                f.write(data_analysis_guidance)
                f.write("\n\n")
            
            f.write("## Next Steps & Resources\n\n")
            
            f.write("### Recommended Next Actions\n\n")
            f.write("1. **Refine your research questions** based on the guidance provided\n")
            f.write("2. **Review the academic sources** listed and obtain full-text versions\n")
            f.write("3. **Create a detailed outline** following the paper structure guidelines\n")
            f.write("4. **Develop your methodology** based on the recommendations\n")
            f.write("5. **Begin your literature review** using the suggested structure\n\n")
            
            f.write("### Additional Resources\n\n")
            f.write("- [Google Scholar](https://scholar.google.com/) - Search for additional academic sources\n")
            f.write("- [Sci-Hub](https://sci-hub.ru/) - Access paywalled academic papers\n")
            f.write("- [Zotero](https://www.zotero.org/) - Free reference management software\n")
            f.write("- [Academic Phrasebank](http://www.phrasebank.manchester.ac.uk/) - Helpful academic writing phrases\n")
            f.write("- [Purdue OWL](https://owl.purdue.edu/owl/purdue_owl.html) - Academic writing resources\n\n")
            
            f.write("---\n\n")
            f.write("*This guidance document was generated by OrcaStatLLM Research Assistant. The sources provided are a starting point and should be supplemented with additional research.*\n")
        
        buffer.add_log(f"Guidance document saved to {file_path}", high_level=True)
        
        pdf_file = None
        try:
            from modules.document.pdf_converter import PDFConverter
            pdf_converter = PDFConverter()
            pdf_file = await pdf_converter.convert_to_pdf(str(file_path), buffer)
            
            if pdf_file:
                buffer.add_log(f"PDF file saved to {pdf_file}", high_level=True)
            else:
                buffer.add_log("Failed to generate PDF file", high_level=True)
        except Exception as e:
            buffer.add_log(f"Error generating PDF: {str(e)}", high_level=True)
            pdf_file = str(file_path).replace('.md', '.pdf')
            
        return str(file_path)
    
    def get_url_tracking(self):
        if hasattr(self.core_researcher, 'url_tracking'):
            return self.core_researcher.url_tracking
        elif hasattr(self.core_researcher, 'research_data'):
            try:
                return self.core_researcher.research_data.get('url_tracking', {})
            except:
                return {}
        return {}
    
    def get_progress(self):
        return self.progress
