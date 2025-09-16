import google.generativeai as genai
import json
import logging
from typing import Dict, Any
from config.settings import Config

logger = logging.getLogger(__name__)

# Configure Gemini with environment variable
try:
    Config.validate()
    genai.configure(api_key=Config.GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Failed to configure Google(Gemini) API: {e}")
    raise


class IntelligentGeminiRouter:
    def __init__(self):
        Config.validate()

        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

        genai.configure(api_key=Config.GOOGLE_API_KEY)

        self.api_call_count = 0
        logger.info("🤖 Gemini router initialized")
    
    def parse_intent(self, user_text: str) -> Dict[str, Any]:
        """Parse intent using Gemini's intelligence"""

        if not user_text or not user_text.strip():
            return {"error": "Empty query provided"}
        
        # Let Gemini do the intelligent parsing
        if Config.DEBUG:
            logger.debug("🤖 Making Gemini API call...")
        
        try:
            self.api_call_count += 1
            result = self._call_gemini_api(user_text)
            
            logger.info(f"📊 Total Gemini API calls this session: {self.api_call_count}")
            return result
            
        except Exception as e:
            logger.error(f"Error in parse_intent: {e}")
            return {"error": f"Failed to parse intent: {e}"}
    
    def _call_gemini_api(self, user_text: str) -> Dict[str, Any]:
        """Let Gemini intelligently understand the user's intent"""
        prompt = f"""
    You are an expert at converting natural language requests into Confluence search queries using CQL (Confluence Query Language).

    CRITICAL: Pay attention to the user's ACTION INTENT, not just the words they use.

    YOUR INTELLIGENCE TASK: Determine if the user is:
    1. RETRIEVING CONTENT of a specific page (get/show/display/read) → confluence_get_page
    2. SEARCHING for multiple pages (find/search/list) → confluence_search
    3. SUMMARIZING a specific page → confluence_get_and_summarize  
    4. SUMMARIZING search results → confluence_search_and_summarize
    5. Getting SPACE OVERVIEW → confluence_space_summary

    CONTENT RETRIEVAL INDICATORS - Use confluence_get_page when user wants to:
    - "Show content of [page title]"
    - "Display page called [page title]" 
    - "Read the [page title] page"
    - "Get [page title]"
    - "Open [page title]"
    - "View [page title]"
    - Any request to ACCESS/VIEW/READ the actual content of a specific page

    SUMMARIZATION INDICATORS - Use confluence_search_and_summarize when user wants:
    - "Overview of pages mentioning [term]"
    - "Summary of pages about [topic]"
    - "Summarize all pages containing [term]"
    - "Give me an overview of [search results]"
    - "What do the pages say about [topic]"
    - "Brief overview of pages with [term]"
    - Any request that wants CONTENT SUMMARY from MULTIPLE pages found via search

    SINGLE PAGE SUMMARIZATION - Use confluence_get_and_summarize when user wants:
    - "Summarize the [page title] page"
    - "Give me a summary of [specific page]"
    - "Overview of the [page title]"
    - Any request to SUMMARIZE a SPECIFIC page by title/ID

    IMPORTANT CQL SYNTAX RULES:
    - Title search: title ~ "search term"
    - Content/body search for single words: text ~ "search term"
    - Content/body search for exact phrases: siteSearch ~ "exact phrase" 
    - Exact title match: title ~ "exact title"
    - Site-wide relevance: siteSearch ~ "search term"
    - Space filtering: space = "SPACE_KEY" AND [other criteria]
    - Page type: type = page
    - Combine with AND: title ~ "roadmap" AND space = "Product_Updates"

    CRITICAL PHRASE HANDLING:
    For compound terms that should be searched as exact phrases, Confluence CQL requires proper phrase syntax. Multi-word technical and business terms must be treated as complete units, not separate words.

    PHRASE IDENTIFICATION - These multi-word concepts should be searched as exact phrases:
    - Technical terms: "IT access", "machine learning", "API endpoints", "database connection", "user authentication"
    - Business processes: "project management", "code review", "quality assurance", "incident response"
    - Product names: "Microsoft Office", "Google Cloud", "Azure DevOps"
    - Department names: "human resources", "customer service", "technical support"

    The key principle: Multi-word terms should be searched as EXACT PHRASES to find documents where those words appear together, not scattered throughout the document.

    EXAMPLES OF INTELLIGENT PHRASE DETECTION:

    Single concepts:
    "Find pages about Docker" → text ~ "Docker"
    "Search for roadmap" → title ~ "roadmap"

    Compound terms (treat as phrases):
     "Show me pages containing IT access" → siteSearch ~  "IT access"
    "Find content mentioning user authentication" → siteSearch ~  "user authentication"  
    "Search for machine learning pages" → siteSearch ~  "machine learning"
    "Look for API endpoints documentation" → siteSearch ~  "API endpoint*"


    Already quoted (definitely exact phrases):
    "Find 'Getting Started Guide'" → siteSearch ~  "Getting Started Guide"

    TOOL SELECTION RULES:
    1. If user wants to GET/READ/VIEW/SHOW/DISPLAY a specific page by ID or title → confluence_get_page
    2. If user wants to SUMMARIZE a specific page → confluence_get_and_summarize  
    3. If user wants to SUMMARIZE multiple pages from search → confluence_search_and_summarize
    4. If user wants to find SIMILAR pages → confluence_find_similar_*
    5. If user wants to LIST ALL pages in a space → confluence_search with space filter
    6. If user wants EXECUTIVE SUMMARY or SPACE OVERVIEWS of entire space → confluence_space_summary
    7. Otherwise for SEARCH/FIND operations → confluence_search

    SPACE KEY MAPPING:
    "Product_Updates" → try "ProductUpd"
    "Product Updates" → try "ProductUpd"

    EXAMPLES:

    CONTENT RETRIEVAL (→ confluence_get_page):
    "Show content of 'May Product Roadmap'" → {{"tool": "confluence_get_page", "parameters": {{"title": "May Product Roadmap"}}}}

    "Display page called 'April Product Release Notes'" → {{"tool": "confluence_get_page", "parameters": {{"title": "April Product Release Notes"}}}}

    "Read the 'RAG Knowledge Base from Confluence' page" → {{"tool": "confluence_get_page", "parameters": {{"title": "RAG Knowledge Base from Confluence"}}}}

    "Get page 12345" → {{"tool": "confluence_get_page", "parameters": {{"page_id": "12345"}}}}

    "View the roadmap page" → {{"tool": "confluence_get_page", "parameters": {{"title": "roadmap"}}}}

    SEARCH OPERATIONS (→ confluence_search):
    "Search for pages titled roadmap" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND title ~ \\"roadmap\\""}}}}

    "Search for pages titled 'Roadmap'" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND title ~ \\"Roadmap\\""}}}}

    "Show pages containing guide in the title" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND title ~ \\"guide\\""}}}}

    "Search for pages containing IT access in body" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND text ~ \\"IT access\\""}}}}

    "Show me pages containing IT access" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND text ~ \\"IT access\\""}}}}

    "look for content mentioning IT access" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND text ~ \\"IT access\\""}}}}

    "Find pages about Docker" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND siteSearch ~ \\"Docker\\""}}}}

    "List all pages in Product_Updates space" → {{"tool": "confluence_search", "parameters": {{"query": "space = \\"Product_Updates\\" AND type = page"}}}}

    SUMMARIZATION:
    "Summarize page titled 'Roadmap'" → {{"tool": "confluence_get_and_summarize", "parameters": {{"title": "Roadmap", "space_key": "test"}}}}

    "Overview of all pages mentioning server" → {{"tool": "confluence_search_and_summarize", "parameters": {{"query": "type = page AND text ~ \\"server\\""}}}}

    "Summary of pages about Docker" → {{"tool": "confluence_search_and_summarize", "parameters": {{"query": "type = page AND siteSearch ~ \\"Docker\\""}}}}

    "Give me an overview of pages containing API" → {{"tool": "confluence_search_and_summarize", "parameters": {{"query": "type = page AND text ~ \\"API\\""}}}}

    "Summarize search results for Docker" → {{"tool": "confluence_search_and_summarize", "parameters": {{"query": "type = page AND siteSearch ~ \\"Docker\\""}}}}
    

    QUERY CONSTRUCTION EXAMPLES:
    "Show me pages containing 'IT access'" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND text ~ \\"IT access\\""}}}}

    "Find pages about machine learning" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND text ~ \\"machine learning\\""}}}}

    "Look for user authentication documentation" → {{"tool": "confluence_search", "parameters": {{"query": "type = page AND text ~ \\"user authentication\\""}}}}

    CRITICAL: Don't overthink it. Use the user's exact words in the CQL query. If they say "roadmap", search for "roadmap". If they say "IT access", search for "IT access". The key is recognizing when multiple words form a single concept that should be kept together in the search.
    "List pages in Knowledge space" → First try: space = "Knowledge" AND type = page → If no results: type = page (search all), then filter/group by spaces containing "Knowledge"

    KEY DECISION RULE:
    - If user wants the CONTENT/VIEW/READ of a specific page → confluence_get_page
    - If user wants to FIND/SEARCH for pages → confluence_search
    - If a space is not specified, assume entire Confluence site
    - If a space has underscores, try removing them for the space key Example: "Product_Updates" → "ProductUpd"
    - If user provides exact space key (like "KnowledgeB") → use it directly
    - If user provides partial/fuzzy space name (like "Knowledge", "know") → search without space filter, then group by space
    - If user wants OVERVIEW/SUMMARY of search results → confluence_search_and_summarize

User request: "{user_text}"

Respond with ONLY valid JSON:
        """
        
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            if not response.text:
                return {"error": "Empty response from Gemini API"}
                
            text = self._clean_response(response.text)
            parsed = json.loads(text)
            parsed["original_query"] = user_text
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": f"Invalid JSON response from Gemini: {e}"}
        
        except ValueError as e:  
            logger.error(f"Response validation error: {e}")
            return {"error": f"Invalid JSON: {e}"}    
        
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {"error": f"API error: {e}"}

    def _clean_response(self, text: str) -> str:
        """Clean up Gemini response to extract JSON"""
        if not text:
            raise ValueError("Empty response text")
            
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
            
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        
        # Validate that we have something that looks like JSON
        if not (text.startswith('{') and text.endswith('}')):
            raise ValueError(f"Response doesn't appear to be JSON: {text[:100]}...")
            
        return text

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "api_calls_this_session": self.api_call_count,
            "model": "gemini-1.5-flash",
            "configured": bool(Config.GEMINI_API_KEY)
        }

# Global router instance with lazy initialization
_router: IntelligentGeminiRouter | None = None

def get_router() -> IntelligentGeminiRouter:
    """Get or create the singleton router"""
    global _router
    if _router is None:
        _router = IntelligentGeminiRouter()
    return _router

def parse_intent(user_text: str) -> Dict[str, Any]:
    """Main entry point for intent parsing"""
    try:
        router = get_router()
        return router.parse_intent(user_text)
    except Exception as e:
        logger.error(f"Error in parse_intent: {e}")
        return {"error": f"Failed to parse intent: {e}"}

def get_stats() -> Dict[str, Any]:
    """Get statistics from the router"""
    try:
        if _router:
            return _router.get_stats()
        return {"api_calls_this_session": 0, "configured": bool(Config.GEMINI_API_KEY)}
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": f"Failed to get stats: {e}"}

def health_check() -> bool:
    """Check if Gemini API is accessible"""
    try:
        # Try to create a router (validates API key)
        router = get_router()
        return True
    except Exception as e:
        logger.error(f"Gemini health check failed: {e}")
        return False