import os
import datetime
import base64
from pathlib import Path
from typing import List, Dict, Callable, Optional, Set
import re
import uuid
import shutil
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.citation import Citation, SourceReference
from modules.document.pdf_converter import PDFConverter

class MarkdownGenerator:
    async def generate_markdown(self, topic: str, title: str, abstract: str, sections: List[Dict], 
                               conclusion: str, buffer: AsyncBuffer, research_dir: Path, 
                               embed_image_func: Callable, references: Optional[Dict] = None,
                               arxiv_insights: Optional[Dict] = None,
                               tables: Optional[List[Dict]] = None) -> str:
        buffer.add_log("Generating final markdown document", high_level=True)
        
        timestamp = datetime.datetime.now().strftime("%B %d, %Y")
        if not references:
            references = {}
            
        if not tables:
            tables = []
            
        if not arxiv_insights:
            arxiv_insights = {"papers": [], "insights": "", "citations": []}
        all_sources = []
        academic_sources = []
        informal_sources = []
        
        for section in sections:
            for source in section["sources"]:
                if source not in all_sources:
                    all_sources.append(source)
                    if any(academic_domain in source.lower() for academic_domain in 
                          ['arxiv', 'doi', '.edu', '.ac.uk', 'researchgate', 'springer', 
                           'sciencedirect', 'jstor', 'ieee', 'mdpi', 'ncbi', 'scielo', 
                           'ssrn', 'journal', 'conference']):
                        academic_sources.append(source)
                    elif any(informal_domain in source.lower() for informal_domain in
                            ['wikipedia', 'blog', 'medium', '.com', '.org', '.net']):
                        informal_sources.append(source)
                    else:
                        academic_sources.append(source)
        markdown = self._generate_title_page(title, timestamp)
        markdown += self._generate_table_of_contents(sections)
        markdown += self._generate_abstract(abstract)
        intro_section = None
        for section in sections:
            if ("introduction" in section['subtopic'].lower() or 
                "overview" in section['subtopic'].lower() or
                "background" in section['subtopic'].lower()):
                intro_section = section
                break
        
        if intro_section:
            markdown += f"## Introduction\n\n"
            if intro_section["image_path"] and os.path.exists(intro_section["image_path"]):
                markdown += await self._add_image(intro_section, embed_image_func, research_dir)
                
            markdown += self._process_section_content(intro_section["content"], references)
        else:
            markdown += f"## Introduction\n\n"
            markdown += f"This research paper examines {topic} from multiple perspectives, analyzing various aspects and implications. The following sections explore different dimensions of this topic based on current research and available information.\n\n"
        if arxiv_insights and arxiv_insights.get("insights"):
            markdown += f"## Literature Review\n\n"
            markdown += f"{arxiv_insights['insights']}\n\n"
        if arxiv_insights and arxiv_insights.get("papers"):
            for paper in arxiv_insights["papers"]:
                markdown += f"* {paper['title']} ({paper['published']})\n"
            markdown += "\n"
        for section in sections:
            if section == intro_section:
                continue
                
            markdown += f"## {section['subtopic']}\n\n"
            if section["image_path"] and os.path.exists(section["image_path"]):
                markdown += await self._add_image(section, embed_image_func, research_dir)
            markdown += self._process_section_content(section['content'], references)
            markdown += "\n"
        if tables and len(tables) > 0:
            markdown += f"## Data Analysis\n\n"
            for table in tables:
                markdown += f"{table['markdown']}\n\n"
        markdown += f"## Conclusion\n\n"
        markdown += conclusion
        markdown += "\n\n"
        markdown += "## References\n\n"
        if academic_sources or (arxiv_insights and arxiv_insights.get("citations")):
            markdown += "### Academic Sources\n\n"
            if arxiv_insights and arxiv_insights.get("citations"):
                for citation in arxiv_insights["citations"]:
                    markdown += f"* {citation}\n"
                markdown += "\n"
            ref_num = len(arxiv_insights.get("citations", [])) + 1
            for source in academic_sources:
                url_match = re.search(r'(https?://[^\s]+)', source)
                title_match = re.search(r'\[(.*?)\]', source)
                
                if url_match and url_match.group(1) in references:
                    ref = references[url_match.group(1)]
                    ref_text = f"{ref_num}. {ref.format_citation('apa')}"
                elif title_match:
                    url = url_match.group(1) if url_match else ""
                    title = title_match.group(1)
                    ref_text = f"{ref_num}. {title}. Retrieved from {url}"
                else:
                    ref_text = f"{ref_num}. {source}"
                
                markdown += f"{ref_text}\n"
                ref_num += 1
            
            markdown += "\n"
        if informal_sources:
            markdown += "## Learned From Resources\n\n"
            markdown += "The following resources provided context and background information that informed our analysis, although they are not cited directly in the academic references:\n\n"
            
            for i, source in enumerate(informal_sources):
                domain = "Web resource"
                if "wikipedia" in source.lower():
                    domain = "Wikipedia"
                elif "blog" in source.lower() or "medium" in source.lower():
                    domain = "Blog post"
                elif ".gov" in source.lower():
                    domain = "Government resource"
                elif ".edu" in source.lower():
                    domain = "Educational resource"
                elif ".org" in source.lower():
                    domain = "Organization resource"
                url_match = re.search(r'(https?://[^\s]+)', source)
                title_match = re.search(r'\[(.*?)\]', source)
                
                if title_match and url_match:
                    markdown += f"* {domain}: [{title_match.group(1)}]({url_match.group(1)})\n"
                elif url_match:
                    markdown += f"* {domain}: {url_match.group(1)}\n"
                else:
                    markdown += f"* {domain}: {source}\n"
        figures_dir = research_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        await self._organize_image_files(sections, figures_dir, buffer)
        readme_path = research_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f"""# {title} - Research Paper

This research paper contains images and formatting that render best when:

1. Viewed in a Markdown viewer that supports embedded images
2. Viewed as a PDF (use the included PDF file or convert the markdown)
3. The `figures` directory must be in the same directory as the markdown file

To ensure proper rendering of all figures and tables, please ensure all files remain in their current directory structure.
""")
        short_name = self.shorten_filename(topic)
        markdown_file = research_dir / f"{short_name}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
            
        buffer.add_log(f"Markdown file saved to {markdown_file}", high_level=True)
        pdf_converter = PDFConverter()
        pdf_file = await pdf_converter.convert_to_pdf(str(markdown_file), buffer)
        
        if pdf_file:
            buffer.add_log(f"PDF file saved to {pdf_file}", high_level=True)
        else:
            buffer.add_log("Failed to generate PDF file", high_level=True)
        
        return str(markdown_file)
    
    def _generate_title_page(self, title: str, timestamp: str) -> str:

        title_page = f"""# {title}

*Research paper generated by OrcaStatLLM Scientist on {timestamp}*
"""
        return title_page
    
    def _generate_abstract(self, abstract: str) -> str:

        return f"""## Abstract

{abstract}

"""
    
    def _generate_table_of_contents(self, sections: List[Dict]) -> str:

        toc = "## Table of Contents\n\n"
        intro_exists = any("introduction" in section['subtopic'].lower() 
                          or "overview" in section['subtopic'].lower() 
                          for section in sections)
        if intro_exists:
            toc += "1. [Introduction](#introduction)\n"
        lit_review_num = 2 if intro_exists else 1
        toc += f"{lit_review_num}. [Literature Review](#literature-review)\n"
        section_num = lit_review_num + 1
        for section in sections:
            if "introduction" in section['subtopic'].lower() or "overview" in section['subtopic'].lower():
                continue
                
            section_link = section['subtopic'].lower().replace(' ', '-')
            section_link = re.sub(r'[^a-z0-9-]', '', section_link)
            toc += f"{section_num}. [{section['subtopic']}](#{section_link})\n"
            section_num += 1
        toc += f"{section_num}. [Data Analysis](#data-analysis)\n"
        section_num += 1
        toc += f"{section_num}. [Conclusion](#conclusion)\n"
        toc += f"{section_num + 1}. [References](#references)\n"
        toc += f"{section_num + 2}. [Learned From Resources](#learned-from-resources)\n"
        
        return toc + "\n"
    
    async def _add_image(self, section: Dict, embed_image_func: Callable, research_dir: Path) -> str:

        try:
            image_path = section["image_path"]
            if not image_path or not os.path.exists(image_path):
                return ""
            figures_dir = research_dir / "figures"
            filename = os.path.basename(image_path)
            dest_path = figures_dir / filename
            
            if os.path.abspath(image_path) != os.path.abspath(dest_path):
                try:
                    figures_dir.mkdir(exist_ok=True)
                    shutil.copy2(image_path, dest_path)
                except Exception as e:
                    print(f"Error copying image: {e}")
            rel_path = f"figures/{filename}"
            image_markdown = f"""<figure>
<img src="{rel_path}" alt="{section['subtopic']} Diagram" style="max-width:90%; margin:0 auto; display:block;">
<figcaption style="text-align:center; font-style:italic;">Figure: Visual representation of {section['subtopic']}</figcaption>
</figure>

"""
            
            return image_markdown
        except Exception as e:
            print(f"Error adding image to markdown: {str(e)}")
            return ""
    
    def _process_section_content(self, content: str, citations: Dict) -> str:

        citation_pattern = r'\[(\d+)\]'
        
        def citation_replacer(match):
            cit_num = match.group(1)
            return f"[{cit_num}]"  # Keep IEEE style citations
        processed_content = re.sub(citation_pattern, citation_replacer, content)
        processed_content = processed_content.replace("**", "**")  # Bold stays the same
        processed_content = processed_content.replace("*", "*")    # Italic stays the same
        
        return processed_content
    
    async def _organize_image_files(self, sections: List[Dict], figures_dir: Path, buffer: AsyncBuffer) -> None:

        buffer.add_log("Organizing image files for better PDF rendering", high_level=True)
        
        for section in sections:
            if section["image_path"] and os.path.exists(section["image_path"]):
                img_filename = os.path.basename(section["image_path"])
                dest_file = figures_dir / img_filename
                figures_dir.mkdir(exist_ok=True)
                if os.path.abspath(section["image_path"]) != os.path.abspath(dest_file):
                    try:
                        shutil.copy2(section["image_path"], dest_file)
                        buffer.add_log(f"Copied image {img_filename} to figures directory")
                        section["image_path"] = str(dest_file)
                    except Exception as e:
                        buffer.add_log(f"Error copying image: {str(e)}")
    
    def shorten_filename(self, name: str, max_length: int = 20) -> str:
        import re
        name = re.sub(r'[^\w\s]', '', name)
        name = name.replace(' ', '_')
        
        if len(name) <= max_length:
            return name
            
        short_hash = str(abs(hash(name)) % 10000)
        name_part_length = max_length - len(short_hash) - 1
        return f"{name[:name_part_length]}_{short_hash}"

    def _add_citation_if_context_matches(self, content: str, citation: SourceReference) -> str:

        if citation.title.lower() in content.lower():
            citation_text = citation.format_citation()
            content += f"\n\n{citation_text}\n"
        return content

    def _align_references_properly(self, content: str) -> str:

        css = """
        <style>
        .reference {
            text-align: left;
            margin-left: 0;
            margin-right: 0;
        }
        </style>
        """
        content = css + content
        return content
