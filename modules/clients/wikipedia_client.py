import wikipedia
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.rate_limiter import RateLimitHandler
from modules.utils.citation import SourceReference

class WikipediaClient:
    def __init__(self, rate_limiter: RateLimitHandler):
        self.rate_limiter = rate_limiter
        wikipedia.set_lang("en")
    
    async def fetch_wikipedia_content(self, topic: str, buffer: AsyncBuffer, references: dict) -> str:
        await self.rate_limiter.wait_if_needed("wikipedia")
        buffer.add_log(f"Searching Wikipedia for: {topic}", high_level=True)
            
        try:
            try:
                summary = wikipedia.summary(topic, auto_suggest=True, sentences=10)
                page = wikipedia.page(topic, auto_suggest=True)
                title = page.title
                content = summary
                buffer.add_log(f"Found Wikipedia summary for '{title}'")
                
                wiki_ref = SourceReference(
                    title=title,
                    url=page.url,
                    source_type="wikipedia",
                )
                wiki_ref.relevance_score = 0.8
                wiki_ref.calculate_scores()
                references[page.url] = wiki_ref
                
            except wikipedia.DisambiguationError as e:
                if e.options:
                    suggestion = e.options[0]
                    buffer.add_log(f"Wikipedia disambiguation page - using suggestion: {suggestion}", high_level=True)
                    summary = wikipedia.summary(suggestion, auto_suggest=False)
                    page = wikipedia.page(suggestion)
                    title = page.title
                    content = summary
                    
                    wiki_ref = SourceReference(
                        title=title,
                        url=page.url,
                        source_type="wikipedia",
                    )
                    wiki_ref.relevance_score = 0.7
                    wiki_ref.calculate_scores()
                    references[page.url] = wiki_ref
                else:
                    raise
            except wikipedia.PageError:
                search_results = wikipedia.search(topic, results=3)
                if not search_results:
                    buffer.add_log("No Wikipedia results found")
                    return ""
                
                suggestion = search_results[0]
                buffer.add_log(f"Direct page not found - using search result: {suggestion}", high_level=True)
                summary = wikipedia.summary(suggestion, auto_suggest=False)
                page = wikipedia.page(suggestion)
                title = page.title
                content = summary
                
                wiki_ref = SourceReference(
                    title=title,
                    url=page.url,
                    source_type="wikipedia",
                )
                wiki_ref.relevance_score = 0.6
                wiki_ref.calculate_scores()
                references[page.url] = wiki_ref
            
            if len(content) < 1000 and hasattr(page, "sections") and page.sections:
                additional_content = []
                for section in page.sections[:3]:
                    try:
                        section_content = page.section(section)
                        if section_content:
                            additional_content.append(f"\n\n== {section} ==\n{section_content}")
                    except:
                        pass
                
                content += "".join(additional_content)
                
                if len(content) > 2500:
                    content = content[:2500] + "... [content truncated]"
            
            buffer.add_log(f"Found Wikipedia content for '{title}' ({len(content)} chars)")
            return f"Wikipedia: {title}\n\n{content}"
            
        except Exception as e:
            buffer.add_log(f"Wikipedia error for {topic}: {str(e)}")
            return ""

