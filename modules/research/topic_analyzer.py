import json
from typing import Dict, List, Any, Callable, Awaitable

class TopicAnalyzer:
    def __init__(self, process_query: Callable[[str, Any], Awaitable[str]], news_client: Any):
        self.process_query = process_query
        self.news_client = news_client
        self.event_keywords = [
            "disaster", "election", "pandemic", "outbreak", "crisis", "attack", "war", 
            "conflict", "scandal", "protest", "rally", "coup", "invasion", "brexit",
            "shooting", "earthquake", "hurricane", "flood", "legislation", "bill",
            "conference", "summit"
        ]
        
    async def analyze_topic(self, topic: str, buffer: Any) -> Dict[str, Any]:

        is_likely_event = any(keyword in topic.lower() for keyword in self.event_keywords)
        try:
            if is_likely_event:
                buffer.add_log("Topic appears to be event-related, performing detailed event analysis", high_level=True)
                event_analysis = await self.news_client.detect_event_topic(topic, buffer, self.process_query)
                if event_analysis is None:
                    buffer.add_log("Event analysis returned None, creating default structure", high_level=True)
                    event_analysis = {
                        "is_event": is_likely_event,  # Use our keyword-based detection as fallback
                        "title": "",  # Will be generated later
                        "news_articles": [],
                        "concept_queries": [f"{topic} overview", f"{topic} definition", f"{topic} examples"],
                        "key_components": [],
                        "regions": [],
                        "region_code": "US",
                        "reasoning": "Fallback detection based on keywords"
                    }
            else:
                buffer.add_log("Topic does not appear to be an event, skipping news analysis", high_level=True)
                event_analysis = {
                    "is_event": False,
                    "title": "",  # Will be generated later
                    "news_articles": [],  # Empty news articles
                    "concept_queries": [f"{topic} overview", f"{topic} definition", f"{topic} examples"],
                    "key_components": [],
                    "regions": [],
                    "region_code": "US",
                    "reasoning": "Not detected as an event based on initial keyword analysis"
                }
        except Exception as e:
            buffer.add_log(f"Error in event analysis: {str(e)}. Using fallback approach.", high_level=True)
            event_analysis = {
                "is_event": False,
                "title": "",
                "news_articles": [],
                "concept_queries": [f"{topic} overview", f"{topic} definition", f"{topic} examples"],
                "key_components": [],
                "regions": [],
                "region_code": "US",
                "reasoning": "Fallback due to error in event analysis"
            }
            
        return event_analysis
        
    async def breakdown_topic(self, topic: str, buffer: Any, research_data: Dict) -> List[str]:

        
        try:
            buffer.add_log(f"Breaking down topic: '{topic}' into searchable components", high_level=True)
            try:
                event_analysis = await self.news_client.detect_event_topic(topic, buffer, self.process_query)
                if event_analysis is None:
                    buffer.add_log("Event analysis returned None, using fallback approach", high_level=True)
                    event_analysis = {
                        "is_event": False,
                        "concept_queries": [f"{topic} overview", f"{topic} definition", f"{topic} applications"]
                    }
                research_data["event_analysis"] = event_analysis
                
            except Exception as e:
                buffer.add_log(f"Error in event detection: {str(e)}. Using fallback approach.", high_level=True)
                event_analysis = {
                    "is_event": False,
                    "concept_queries": [f"{topic} overview", f"{topic} definition", f"{topic} applications"]
                }
                research_data["event_analysis"] = event_analysis
            if event_analysis.get("is_event", False):
                buffer.add_log(f"Topic '{topic}' identified as event-related - using event-specific queries", high_level=True)
                event_queries = event_analysis.get("event_queries", [])
                if not event_queries:
                    event_queries = [f"{topic} latest developments", f"{topic} timeline", f"{topic} analysis"]
                news_context = ""
                for article in event_analysis.get("news_articles", [])[:3]:  # Use top 3 articles for context
                    title = article.get('title', 'Untitled article')
                    news_context += f"- {title}\n"
                if not news_context:
                    news_context = "(No specific news articles found)\n"
                
                prompt = f"""
You are a research expert. The topic "{topic}" appears to be related to real-world events.
Here are some recent news headlines about this topic:

{news_context}

Break down this event-based topic into 5-8 distinct search queries that together
would provide comprehensive coverage. Each query should:

1. Focus on different aspects/dimensions of the event (background, timeline, impacts, stakeholders, etc.)
2. Be specific enough to yield relevant results
3. Include important keywords and context from the domain
4. Include relevant timeframes or context when appropriate

Format your response as a JSON array of strings, with each string being a search query.
Example: ["Ukraine conflict latest developments", "Ukraine conflict historical background", "Ukraine conflict economic impacts"]

Only return the JSON array, nothing else.
"""
                
                buffer.add_log(f"Generating event-specific search components", high_level=True)
                try:
                    response = await self.process_query(prompt, buffer)
                    
                    json_str = response
                    if "```json" in response:
                        json_str = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        json_str = response.split("```")[1].strip()
                        
                    llm_components = json.loads(json_str)
                    all_components = event_queries + llm_components
                    components = []
                    for component in all_components:
                        normalized = component.lower().strip()
                        if not any(normalized in c.lower() for c in components):
                            components.append(component)
                            
                    buffer.add_log(f"Generated {len(components)} event-specific search components")
                    return components[:8]  # Limit to 8 components
                except Exception as e:
                    buffer.add_log(f"Error parsing event search components: {str(e)}. Using event-specific fallback method.")
                    return event_queries + [f"{topic} timeline", f"{topic} analysis", f"{topic} impact"]
                    
            else:
                buffer.add_log(f"Topic '{topic}' identified as concept-based - using educational/technical approach", high_level=True)
                concept_queries = event_analysis.get("concept_queries", [])
                if concept_queries and len(concept_queries) >= 3:
                    buffer.add_log(f"Using {len(concept_queries)} pre-generated concept queries from event analysis")
                    return concept_queries
                
                prompt = f"""
You are a research expert. Break down the concept/topic "{topic}" into 5-8 distinct search queries that together
would provide comprehensive coverage of the topic. Each query should:

1. Focus on a different aspect/dimension of the topic (definition, methodology, applications, history, etc.)
2. Be specific enough to yield relevant academic or technical results
3. Include important keywords and context from the domain
4. Be formulated to find high-quality, educational content

Format your response as a JSON array of strings, with each string being a search query.
Example: ["machine learning fundamentals explained", "machine learning algorithms comparison", "practical applications of machine learning in healthcare"]

Only return the JSON array, nothing else.
"""
                buffer.add_log(f"Breaking down concept-based topic into searchable components", high_level=True)
                try:
                    response = await self.process_query(prompt, buffer)
                    
                    json_str = response
                    if "```json" in response:
                        json_str = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        json_str = response.split("```")[1].strip()
                        
                    components = json.loads(json_str)
                    buffer.add_log(f"Generated {len(components)} concept-based search components")
                    return components
                except Exception as e:
                    buffer.add_log(f"Error parsing search components: {str(e)}. Using concept-based fallback method.")
                    return [f"{topic} definition", f"{topic} techniques", f"{topic} applications", 
                            f"{topic} examples", f"{topic} benefits", f"{topic} challenges"]
        except Exception as e:
            buffer.add_log(f"Critical error in topic breakdown: {str(e)}. Using emergency fallback.", high_level=True)
            return [f"{topic} overview", f"{topic} analysis", f"{topic} examples", 
                    f"{topic} research", f"{topic} applications", f"{topic} history"]
                    
    async def identify_subtopics(self, topic: str, buffer: Any, research_data: Dict) -> List[Dict]:

        event_analysis = research_data.get("event_analysis")
        if not event_analysis:
            event_analysis = await self.news_client.detect_event_topic(topic, buffer)
            research_data["event_analysis"] = event_analysis
        
        is_event = event_analysis.get("is_event", False)
        
        if is_event:
            news_context = ""
            for article in event_analysis.get("news_articles", [])[:3]:
                news_context += f"- {article['title']}\n"
            
            prompt = f"""
You are a scientific research expert planning a comprehensive paper on the current event:
"{topic}"

Here are some recent news headlines about this event:
{news_context}

Please identify 5-8 key subtopics that should be covered in this research paper. 
For each subtopic, also provide 2-3 specific search queries that would help gather information.

Consider including:
- Background and historical context
- Current status and recent developments
- Key stakeholders and their perspectives
- Impact analysis (social, economic, political, etc.)
- Comparative analysis with similar historical events
- Future implications

Format your response as a JSON array where each item is an object with:
1. "subtopic": The name of the subtopic
2. "search_queries": An array of search queries for this subtopic

Example:
[
  {{
    "subtopic": "Historical Background of {topic}",
    "search_queries": ["{topic} historical context", "{topic} origins timeline"]
  }},
  ...
]
"""
        else:
            prompt = f"""
You are a scientific research expert. You are planning a comprehensive research paper on the topic:
"{topic}"

Please identify 5-8 key subtopics that should be covered in this research paper. 
For each subtopic, also provide 2-3 specific search queries that would help gather information.

Format your response as a JSON array where each item is an object with:
1. "subtopic": The name of the subtopic
2. "search_queries": An array of search queries for this subtopic

Example:
[
  {{
    "subtopic": "Historical Background",
    "search_queries": ["history of {topic}", "{topic} evolution timeline"]
  }},
  ...
]
"""
        
        buffer.add_log(f"Identifying subtopics for: {topic}", high_level=True)
        response = await self.process_query(prompt, buffer)
        
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].strip()
            
            subtopics_data = json.loads(json_str)
            buffer.add_log(f"Successfully identified {len(subtopics_data)} subtopics", high_level=True)
            return subtopics_data
        except Exception as e:
            buffer.add_log(f"Error parsing subtopics: {str(e)}. Using fallback method.")
            if is_event:
                subtopics = [
                    {"subtopic": f"Introduction to {topic}", 
                     "search_queries": [f"{topic} overview", f"{topic} latest developments"]},
                    {"subtopic": "Historical Context", 
                     "search_queries": [f"{topic} historical background", f"{topic} timeline"]},
                    {"subtopic": "Current Situation", 
                     "search_queries": [f"{topic} current status", f"{topic} recent updates"]},
                    {"subtopic": "Key Stakeholders", 
                     "search_queries": [f"{topic} key players", f"{topic} organizations involved"]},
                    {"subtopic": "Impact Analysis", 
                     "search_queries": [f"{topic} impacts", f"{topic} consequences"]},
                    {"subtopic": "Future Implications", 
                     "search_queries": [f"{topic} future outlook", f"{topic} predictions"]}
                ]
            else:
                subtopics = [
                    {"subtopic": "Introduction to " + topic, 
                     "search_queries": [f"introduction to {topic}", f"{topic} basics"]},
                    {"subtopic": "Historical Background", 
                     "search_queries": [f"history of {topic}", f"{topic} timeline"]},
                    {"subtopic": "Current State of Research", 
                     "search_queries": [f"latest research on {topic}", f"{topic} recent studies"]},
                    {"subtopic": "Methodology", 
                     "search_queries": [f"{topic} methodology", f"research methods for {topic}"]},
                    {"subtopic": "Future Directions", 
                     "search_queries": [f"future of {topic}", f"{topic} upcoming developments"]}
                ]
            
            buffer.add_log(f"Generated {len(subtopics)} subtopics using fallback method", high_level=True)
            return subtopics

