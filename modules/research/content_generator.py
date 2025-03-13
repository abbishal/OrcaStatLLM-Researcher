from typing import Dict, List, Any, Callable, Awaitable

class ContentGenerator:
    def __init__(self, process_query: Callable[[str, Any], Awaitable[str]]):
        self.process_query = process_query
        
    async def generate_section_content(self, topic: str, subtopic: str, research_material: str, buffer: Any) -> str:
        prompt = f"""
You are writing a section of a professional research paper on "{topic}" - specifically the section about "{subtopic}".
Use the following research material (which contains summaries of multiple sources) to write a comprehensive, 
academically rigorous section (800-1200 words):

{research_material}

Write in a natural, engaging academic style with proper citations indicated as [1], [2], etc. where each number corresponds to the sources in the research material.
Important guidelines to follow:
- Use varied sentence structure and lengths - mix shorter sentences with longer, more complex ones
- Include occasional rhetorical questions to engage readers
- Use transitional phrases naturally (e.g., "However", "Moreover", "Interestingly")
- Incorporate thoughtful observations and analytical insights that feel like they come from a human researcher
- Avoid formulaic paragraph structures and repetitive sentence patterns
- Include occasional colloquial but academically appropriate phrases
- Maintain an authentic academic voice without sounding overly formal or robotic
- Make appropriate use of first-person plural when discussing implications (e.g., "We can observe that...")
- Include some nuanced points that show critical thinking, not just summarization
- Identify gaps or contradictions in the research naturally, as a human researcher would
- Use proper technical language and domain-specific terminology appropriately

Ensure the writing sounds like it was written by a thoughtful human academic rather than AI - with natural flow, 
varied expressions, and thoughtful analysis.

This is for an academic audience, so maintain appropriate scholarly tone while ensuring the text feels natural and engaging.
"""

        buffer.add_log(f"Generating content for section: {subtopic}", high_level=True)
        response = await self.process_query(prompt, buffer)
        buffer.add_log(f"Successfully generated content for section: {subtopic}", high_level=True)
        
        return response
        
    async def generate_title(self, topic: str, buffer: Any) -> str:
        prompt = f"""
Generate a compelling, engaging academic title for a research paper on "{topic}".

The title should be:
1. Concise yet descriptive (10-15 words maximum)
2. Include key concepts related to the topic
3. Appropriate for an academic journal
4. Slightly intriguing to capture reader interest
5. Sound like it was written by a human researcher

Avoid formulaic title structures. Consider using:
- A thought-provoking question
- A creative but relevant metaphor
- A clear main title with an explanatory subtitle
- A title that hints at your findings or perspective

Provide only the title without any additional text or explanations.
"""
        buffer.add_log(f"Generating academic title for topic: {topic}", high_level=True)
        title = await self.process_query(prompt, buffer)
        
        title = title.strip().strip('"\'')
        
        buffer.add_log(f"Generated title: {title}", high_level=True)
        return title
        
    async def generate_abstract(self, topic: str, sections: List[Dict], 
                               combined_insights: Dict, buffer: Any) -> str:
        section_titles = [section["subtopic"] for section in sections]
        academic_insights = combined_insights.get("insights", "")
        
        prompt = f"""
You are writing an abstract for a research paper on "{topic}".
The paper covers these sections: {', '.join(section_titles)}.

Academic insights from published papers:
{academic_insights[:300]}

Write a natural, engaging abstract (250-300 words) that:
1. Introduces the research topic and its significance
2. Briefly mentions the main aspects covered in the paper
3. Highlights key findings or insights
4. Includes relevant academic context based on the provided insights
5. Concludes with implications or significance of the research

Make the abstract sound like it was written by a thoughtful human researcher:
- Vary sentence length and structure
- Use natural transitions between ideas
- Avoid overly formulaic expressions
- Include one thought-provoking statement or question
- Write with confidence but avoid excessive formality
- Employ an engaging yet scholarly tone
- Use active voice where appropriate

The abstract should be concise, scholarly, and give readers a clear understanding of what the paper covers,
while maintaining a natural human writing style.
"""
        
        buffer.add_log("Generating abstract for the research paper", high_level=True)
        abstract = await self.process_query(prompt, buffer)
        buffer.add_log(f"Abstract generated successfully ({len(abstract)} characters)", high_level=True)
        return abstract
        
    async def generate_conclusion(self, topic: str, sections: List[Dict], 
                                 combined_insights: Dict, buffer: Any) -> str:
        section_summaries = []
        for section in sections:
            content = section["content"]
            summary = content[:250] + "..." if len(content) > 250 else content
            section_summaries.append(f"Section '{section['subtopic']}': {summary}")
        
        academic_insights = combined_insights.get("insights", "")
        
        prompt = f"""
You are writing the conclusion for a research paper on "{topic}".
The paper includes these sections with the following key points:

{chr(10).join(section_summaries)}

Academic insights from published papers:
{academic_insights[:300]}

Write a natural, thoughtful conclusion (600-800 words) that:
1. Summarizes the main findings across all sections
2. Synthesizes the findings into a cohesive understanding
3. Relates your findings to the academic literature
4. Discusses limitations of current research
5. Suggests specific directions for future research
6. Ends with the broader implications and significance of this topic

Make the conclusion sound like it was written by a thoughtful human academic:
- Use a mix of sentence structures and lengths for natural flow
- Include occasional first-person plural perspective (e.g., "Our analysis suggests...")
- Add thoughtful reflections that demonstrate critical thinking
- Use natural transitions between paragraphs and ideas
- Incorporate some nuanced observations about the research
- Express genuine intellectual curiosity about future directions
- Avoid overly formulaic or rigid structure
- Include an occasional subtle personal insight where appropriate

The conclusion should tie together all sections and provide a meaningful, natural-sounding closing to the research paper,
with the authentic voice of a human researcher who is deeply engaged with the topic.
"""
        
        buffer.add_log("Generating conclusion for the research paper", high_level=True)
        conclusion = await self.process_query(prompt, buffer)
        buffer.add_log(f"Conclusion generated successfully ({len(conclusion)} characters)", high_level=True)
        return conclusion
        
    async def summarize_content(self, content: str, source_type: str, topic: str, buffer: Any) -> str:

        max_content_length = 3000
        truncated_content = content[:max_content_length] + "..." if len(content) > max_content_length else content
        
        prompt = f"""
You are an academic research assistant with a natural writing style. Summarize the following {source_type} content about "{topic}".
Extract key information, statistics, methodologies, and findings that would be valuable for an academic paper.

Content:
{truncated_content}

Create a concise summary (200-300 words) that:
1. Identifies the main points relevant to {topic}
2. Extracts factual information and data
3. Notes any methodologies or approaches described
4. Highlights conclusions or insights
5. Maintains a scholarly but natural tone

Write like a thoughtful human researcher would, with varied sentence structure, 
natural transitions, and genuine intellectual engagement with the material.
Avoid formulaic expressions and overly mechanical language.

The summary should read as if written by a human academic, suitable for integration into a research paper.
"""
        
        try:
            summary = await self.process_query(prompt, buffer)
            if buffer.verbose:
                buffer.add_log(f"Generated summary of {len(summary)} chars for source")
            return summary
        except Exception as e:
            buffer.add_log(f"Error generating content summary: {str(e)}")
            return "Content processing failed. Please see original source."

