from src.gemini_router import parse_intent
from src.confluence_client import call_tool
import json
import re
import google.generativeai as genai
from config.settings import Config
import logging

logger = logging.getLogger(__name__)


def summarize_with_gemini(title, content):
    """Summarize content using Gemini API"""   
    
    try:
        # Truncate content if too long to avoid token limits
        if len(content) > 8000:
            content = content[:8000] + "\n\n[Content truncated for summarization...]"
        
        prompt = f"""
        Please provide a concise summary of the following Confluence page content.
        Focus on the key points, main ideas, and important information.
        Keep the summary clear and well-structured.

        Page Title: {title}
        
        Content:
        {content}
        
        Summary:
        """
        
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def generate_space_executive_summary(pages_data, space_key):
    """Generate an executive summary of all pages in a space using Gemini"""
    import google.generativeai as genai
    
    try:
        if not pages_data:
            return f"No pages found in space '{space_key}' to summarize."
        
        # Prepare page overviews for analysis
        pages_overview = ""
        for i, page in enumerate(pages_data[:15], 1):  # Limit to 15 pages to avoid token limits
            title = page.get("title", "Unknown")
            # Try to get excerpt or use title as context
            excerpt = clean_html_content(page.get("excerpt", ""))
            if not excerpt:
                excerpt = f"Page about {title.lower()}"
            
            pages_overview += f"{i}. **{title}**\n   {excerpt[:150]}...\n\n"
        
        total_pages = len(pages_data)
        analyzed_pages = min(len(pages_data), 15)
        
        prompt = f"""
        You are creating an executive summary for a Confluence space. Analyze the following pages and create a comprehensive, one-paragraph executive summary that captures the main themes, purposes, and key topics covered across all pages.

        Space: {space_key}
        Total Pages: {total_pages}
        Analyzed Pages: {analyzed_pages}

        Pages Overview:
        {pages_overview}

        Please provide:
        1. A comprehensive one-paragraph executive summary that synthesizes the main themes and purposes
        2. Key topics/themes identified (as bullet points)
        3. Overall assessment of the space's focus and utility

        Executive Summary:
        """
        
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        return f"Error generating space summary: {str(e)}"

def handle_space_summary(space_key):
    """Handle space-wide executive summary generation"""
    if Config.DEBUG:
        logger.debug(f"📊 Generating executive summary for space: {space_key}")
    
    # Step 1: Get all pages in the space
    list_response = call_tool("confluence_search", {
        "query": f"space = \"{space_key}\" AND type = page",
        "limit": 50
    })
    
    pages_data = extract_search_results(list_response)
    
    if not pages_data:
        return f"❌ No pages found in space '{space_key}' or space does not exist."
    
    # Step 2: Generate executive summary
    summary = generate_space_executive_summary(pages_data, space_key)
    
    # Step 3: Format the response
    header = f"📊 **Executive Summary for Space '{space_key}'**\n"
    header += f"*Based on analysis of {len(pages_data)} pages*\n\n"
    
    return header + summary


def format_confluence_response(tool_name: str, response: dict, original_query: str = None, action: str = None) -> str:
    """Format the MCP response into a user-friendly message - simplified"""
    
    # Check for errors first
    if "error" in response:
        return f"❌ Error: {response['error']}"
    
    result = response.get("result", {})
    if result.get("isError", False):
        error_content = result.get("content", [])
        if error_content:
            error_text = error_content[0].get("text", "Unknown error")
            return f"❌ Operation failed: {error_text}"
    
    # Extract content
    content = result.get("content", [])
    if not content:
        return "✅ Operation completed successfully"
    
    content_text = content[0].get("text", "") if content else ""
    if not content_text:
        return "✅ Operation completed successfully"
    
    # Parse JSON content
    try:
        parsed_content = json.loads(content_text)
        
        if tool_name == "confluence_search":
            return format_search_results(parsed_content, original_query)
        elif tool_name == "confluence_get_page":
            return format_page_content(parsed_content, action, original_query)
        else:
            # Other tools - return formatted JSON
            return f"✅ {tool_name} completed:\n```json\n{json.dumps(parsed_content, indent=2)}\n```"
    
    except json.JSONDecodeError:
        # Return raw text if not JSON
        return f"✅ {tool_name} completed:\n{content_text}"

def format_search_results(parsed_content, original_query):
    """Format search results"""
    if not isinstance(parsed_content, list) or len(parsed_content) == 0:
        search_context = extract_search_context(original_query)
        return f"🔍 No pages found{search_context}.\n💡 Try different keywords or broader search terms."
    
    results = []
    for i, item in enumerate(parsed_content[:15], 1):
        title = item.get("title", "Unknown Title")
        space_info = item.get("space", {})
        if isinstance(space_info, dict):
            space_name = space_info.get("name") or space_info.get("key", "Unknown")
        else:
            space_name = str(space_info)
            
        page_id = item.get("id", "")
        url = item.get("url", "")
        
        result_line = f"{i}. **{title}** (Space: {space_name}, ID: {page_id})"
        
        # Add excerpt if available
        excerpt = item.get("excerpt", "")
        if excerpt:
            clean_excerpt = clean_html_content(excerpt)
            if len(clean_excerpt) > 120:
                clean_excerpt = clean_excerpt[:120] + "..."
            result_line += f"\n   📄 {clean_excerpt}"
        
        results.append(result_line)
        if url:
            results.append(f"   🔗 {url}")
        results.append("")  # Empty line
    
    total_found = len(parsed_content)
    showing = min(len(parsed_content), 15)
    search_context = extract_search_context(original_query)
    
    header = f"🔍 Found {total_found} page(s){search_context}, showing {showing}:\n\n"
    return header + "\n".join(results)

def format_page_content(parsed_content, action, original_query):
    """Format page content"""
    # Extract page info
    if "metadata" in parsed_content:
        metadata = parsed_content["metadata"]
        title = metadata.get("title", "Unknown")
        space_info = metadata.get("space", {})
        space_name = space_info.get("name", space_info.get("key", "Unknown")) if isinstance(space_info, dict) else str(space_info)
        content_obj = metadata.get("content", {})
        content_preview = content_obj.get("value", "") if isinstance(content_obj, dict) else ""
    else:
        title = parsed_content.get("title", "Unknown")
        space_info = parsed_content.get("space", {})
        space_name = space_info.get("name", space_info.get("key", "Unknown")) if isinstance(space_info, dict) else str(space_info)
        content_preview = parsed_content.get("content", "")
    
    # Handle summarization
    if action == "summarize_page" and content_preview:
        clean_content = clean_html_content(content_preview)
        if clean_content:
            summary = summarize_with_gemini(title, clean_content)
            return f"📋 **Summary of {title}** (Space: {space_name})\n\n{summary}"
        else:
            return f"❌ Could not extract content from page '{title}' for summarization."
    
    # Handle search-style requests (user wants list, not full content)
    if original_query and any(phrase in original_query.lower() for phrase in ["show pages", "pages containing", "find pages"]):
        url = parsed_content.get("_links", {}).get("webui", "")
        return f"📄 **{title}** (Space: {space_name}, ID: {parsed_content.get('id', 'Unknown')})\n🔗 {url}"
    
    # Regular content display
    if content_preview:
        clean_content = clean_html_content(content_preview)
        if len(clean_content) > 1500:
            content_display = clean_content[:1500] + "\n\n... [Content truncated - use summarization for full overview]"
        else:
            content_display = clean_content
    else:
        content_display = "No content available"
    
    return f"📄 **{title}** (Space: {space_name})\n\n{content_display}"

def extract_search_context(original_query):
    """Extract meaningful context from the original search query - simplified"""
    if not original_query:
        return ""
    
    query_lower = original_query.lower()
    
    # Simple pattern matching for common search contexts
    if "titled" in query_lower or "title" in query_lower:
        return " in title"
    elif "containing" in query_lower or "mentioning" in query_lower:
        return " in content"
    elif any(word in query_lower for word in ["about", "on", "regarding"]):
        return " by topic"
    
    return ""

def clean_html_content(content):
    """Clean HTML content and format for display"""
    if not content:
        return ""
    
    # Remove HTML tags
    clean_content = re.sub(r'<[^>]+>', '', content)
    # Fix escaped characters
    clean_content = re.sub(r'\\n', '\n', clean_content)
    clean_content = re.sub(r'\\(.)', r'\1', clean_content)
    # Normalize whitespace but preserve paragraphs
    clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content)
    clean_content = re.sub(r'[ \t]+', ' ', clean_content)
    return clean_content.strip()

def extract_search_results(response):
    """Extract search results from MCP response"""
    try:
        content = response.get("result", {}).get("content", [])
        if not content:
            return []
        raw_text = content[0].get("text", "[]")
        parsed = json.loads(raw_text)
        # If the parsed content is already a list, return it as-is
        if isinstance(parsed, list):
            return parsed
        # If it's a dict (e.g., a page object returned unexpectedly), try to coerce to a single-item list
        if isinstance(parsed, dict):
            coerced = {}
            if "id" in parsed:
                coerced["id"] = parsed.get("id")
            if "title" in parsed:
                coerced["title"] = parsed.get("title")
            if "space" in parsed:
                coerced["space"] = parsed.get("space")
            if coerced:
                return [coerced]
            return []
        # Any other type, return empty
        return []
    except:
        return []

def extract_page_content(response):
    """Extract page content from MCP response"""
    try:
        content = response.get("result", {}).get("content", [])
        if content:
            page_data = json.loads(content[0].get("text", "{}"))
            # Handle nested content structure
            if "metadata" in page_data:
                content_obj = page_data["metadata"].get("content", {})
                if isinstance(content_obj, dict) and "value" in content_obj:
                    return content_obj["value"]
            return page_data.get("content", "")
        else:
            return ""
    except:
        return ""

def summarize_multiple_pages(search_results, search_term=""):
    """Summarize content from multiple pages"""
    if not search_results:
        return "❌ No pages found to summarize."
    
    page_summaries = []
    context = f" related to '{search_term}'" if search_term else ""
    
    # Process top 5 results to avoid overwhelming output
    for i, result in enumerate(search_results[:5], 1):
        page_id = result.get("id")
        title = result.get("title", "Unknown Title")
        
        if page_id:
            if Config.DEBUG:
                logger.debug(f"📄 Getting content for page {i}: {title}")
            page_response = call_tool("confluence_get_page", {"page_id": page_id})
            page_content = extract_page_content(page_response)
            
            if page_content:
                clean_content = clean_html_content(page_content)
                if clean_content:
                    summary = summarize_with_gemini(title, clean_content)
                    page_summaries.append(f"**{i}. {title}**\n{summary}")
                else:
                    page_summaries.append(f"**{i}. {title}**\n(No content available for summarization)")
            else:
                page_summaries.append(f"**{i}. {title}**\n(Could not retrieve content)")
    
    if page_summaries:
        header = f"📋 **Summary of {len(page_summaries)} page(s){context}:**\n\n"
        footer = f"\n\n💡 Summarized top {len(page_summaries)} of {len(search_results)} found pages."
        return header + "\n\n---\n\n".join(page_summaries) + footer
    else:
        return f"❌ Could not retrieve content from any pages{context} for summarization."

def handle_request(user_text: str):
    """Handle a user request end-to-end with enhanced capabilities"""
    try:
        # Step 1: Parse intent with Gemini
        tool_call = parse_intent(user_text)

        # Add type checking
        if isinstance(tool_call, str):
            return f"❌ Error parsing request: {tool_call}"
            
        if not isinstance(tool_call, dict):
            return f"❌ Invalid response format from intent parser"

        if Config.DEBUG:
            print(f"🎯 Intent: {tool_call.get('tool', 'unknown')} with {len(tool_call.get('parameters', {}))} params")
            print(f"🔍 Generated CQL query: {tool_call.get('parameters', {}).get('query', 'No query found')}")
        
        # Check for parsing errors
        if "error" in tool_call:
            return f"❌ Could not understand request: {tool_call['error']}"
        
        tool_name = tool_call.get("tool")
        parameters = tool_call.get("parameters", {})
        action = tool_call.get("action")
        search_term = tool_call.get("search_term", "")
        
        if not tool_name:
            return "❌ No valid tool identified for your request."

         # Handle special space summary tool - NEW
        if tool_name == "confluence_space_summary":
            space_key = parameters.get("space_key", "test")
            return handle_space_summary(space_key)
        
        # Handle special tools that don't exist in MCP but are used for routing
        elif tool_name == "confluence_search_and_summarize":
            # This is search-based summarization
            print(f"📋 Step 1: Searching for pages to summarize...")
            search_response = call_tool("confluence_search", parameters)
            search_results = extract_search_results(search_response)
            
            if search_results:
                print(f"📋 Step 2: Summarizing {len(search_results)} found pages...")
                return summarize_multiple_pages(search_results, search_term)
            else:
                return f"🔍 No pages found{' for ' + search_term if search_term else ''} to summarize."
        
        elif tool_name == "confluence_get_and_summarize":
            # This is direct page summarization
            print(f"📋 Getting page content for summarization...")
            # Check if we need to resolve the space_key first
            if "title" in parameters and "space_key" not in parameters:
                print("🔍 Step 1: Searching to find page space for summarization...")
                title = parameters["title"]
                
                # Search for the page first
                search_response = call_tool("confluence_search", {
                    "query": f"type = page AND title ~ \"{title}\"",
                    "limit": 5
                })
                
                search_results = extract_search_results(search_response)
                
                if search_results:
                    # Find exact title match or best match
                    best_match = None
                    for result in search_results:
                        if result.get("title", "").lower() == title.lower():
                            best_match = result
                            break
                    
                    if not best_match:
                        best_match = search_results[0]  # Take first result
                    
                    # Extract space key
                    space_info = best_match.get("space", {})
                    space_key = space_info.get("key") if isinstance(space_info, dict) else None
                    
                    if space_key:
                        print(f"🔍 Step 2: Found page in space '{space_key}', getting content for summarization...")
                        parameters["space_key"] = space_key
                        response = call_tool("confluence_get_page", parameters)
                        return format_confluence_response("confluence_get_page", response, tool_call.get("original_query"), "summarize_page")
                    else:
                        return f"❌ Found page '{title}' but couldn't determine its space"
                else:
                    return f"❌ No page found with title '{title}'"
            else:
                # Direct call with page_id or title + space_key
                response = call_tool("confluence_get_page", parameters)
                return format_confluence_response("confluence_get_page", response, tool_call.get("original_query"), "summarize_page")

        elif tool_name == "confluence_get_page":
            # If only a title is provided, attempt a direct call first. Some backends accept title-only.
            if "title" in parameters and "space_key" not in parameters and "page_id" not in parameters:
                # Direct probe call
                response = call_tool(tool_name, parameters)
                try:
                    content = response.get("result", {}).get("content", [])
                    raw_text = content[0].get("text", "{}") if content else "{}"
                    parsed = json.loads(raw_text)
                except Exception:
                    parsed = {}
                
                # If we received a page-like dict, format and return
                if isinstance(parsed, dict) and ("content" in parsed or "metadata" in parsed or "title" in parsed):
                    return format_confluence_response(tool_name, response, tool_call.get("original_query"), action)
                
                # If we received a list, treat it as search results and reuse it to resolve space_key
                if isinstance(parsed, list) and len(parsed) > 0:
                    title = parameters["title"]
                    best_match = None
                    for item in parsed:
                        if isinstance(item, dict) and item.get("title", "").lower() == title.lower():
                            best_match = item
                            break
                    if not best_match:
                        best_match = parsed[0] if isinstance(parsed[0], dict) else None
                    if best_match:
                        space_info = best_match.get("space", {}) if isinstance(best_match, dict) else {}
                        space_key = space_info.get("key") if isinstance(space_info, dict) else None
                        if space_key:
                            print(f"🔍 Step 2: Found page in space '{space_key}', getting content...")
                            parameters["space_key"] = space_key
                            response = call_tool(tool_name, parameters)
                            return format_confluence_response(tool_name, response, tool_call.get("original_query"), action)
                    return f"❌ No page found with title '{title}'"
                
                # As a last resort, perform an explicit search to resolve space
                print("🔍 Step 1: Searching to find page space...")
                title = parameters["title"]
                search_response = call_tool("confluence_search", {
                    "query": f"type = page AND title ~ \"{title}\"",
                    "limit": 5
                })
                search_results = extract_search_results(search_response)
                if search_results:
                    best_match = None
                    for result in search_results:
                        if result.get("title", "").lower() == title.lower():
                            best_match = result
                            break
                    if not best_match:
                        best_match = search_results[0]
                    space_info = best_match.get("space", {})
                    space_key = space_info.get("key") if isinstance(space_info, dict) else None
                    if space_key:
                        print(f"🔍 Step 2: Found page in space '{space_key}', getting content...")
                        parameters["space_key"] = space_key
                        response = call_tool(tool_name, parameters)
                        return format_confluence_response(tool_name, response, tool_call.get("original_query"), action)
                    return f"❌ Found page '{title}' but couldn't determine its space"
                return f"❌ No page found with title '{title}'"
            
            # Otherwise, we have page_id or title+space_key; direct call is sufficient
            response = call_tool(tool_name, parameters)
            return format_confluence_response(tool_name, response, tool_call.get("original_query"), action)

        # Handle special case for listing pages - map to search
        elif tool_name == "confluence_list_pages":
            space_key = parameters.get("space_key", "test")
            print(f"📋 Listing all pages in space: {space_key}")
            
            # Convert to search query for the space
            search_params = {
                "query": f"space = \"{space_key}\" AND type = page",
                "limit": 50
            }
            response = call_tool("confluence_search", search_params)
            return format_confluence_response("confluence_search", response, tool_call.get("original_query"))

        # Handle special summarization flows based on action
        elif action == "summarize_search_results":
            print(f"📋 Step 1: Searching for pages to summarize...")
            search_response = call_tool("confluence_search", parameters)
            search_results = extract_search_results(search_response)
            
            if search_results:
                print(f"📋 Step 2: Summarizing {len(search_results)} found pages...")
                return summarize_multiple_pages(search_results, search_term)
            else:
                return f"🔍 No pages found{' for ' + search_term if search_term else ''} to summarize."
        
        elif action == "summarize_page":
            # Direct page summarization
            print(f"📋 Getting page content for summarization...")
            response = call_tool(tool_name, parameters)
            return format_confluence_response(tool_name, response, tool_call.get("original_query"), action)

        elif action == "summarize_space":
            # Space-wide summarization
            space_key = parameters.get("space_key", "test")
            return handle_space_summary(space_key)
        
        # Handle content requests that need search-then-get flow
        is_content_request = any(word in user_text.lower() for word in ["get", "show", "content", "read", "view"])
        is_search_by_title = "title" in user_text.lower() and any(word in user_text.lower() for word in ["with", "containing", "in"]) 
        
        if is_content_request and is_search_by_title and tool_name == "confluence_search":
            print(f"🔧 Step 1: Searching for pages...")
            search_response = call_tool("confluence_search", parameters)
            search_results = extract_search_results(search_response)
            
            if search_results and len(search_results) > 0:
                # Get the first (most relevant) result
                best_match = search_results[0]
                page_id = best_match.get("id")
                
                if page_id:
                    print(f"🔧 Step 2: Getting content for page ID {page_id}...")
                    page_response = call_tool("confluence_get_page", {"page_id": page_id})
                    return format_confluence_response("confluence_get_page", page_response, tool_call.get("original_query"))
                else:
                    return "❌ Found page but couldn't retrieve its ID for content fetching."
            else:
                return "🔍 No pages found matching your search criteria."

        # Regular single-step processing
        else:
            print(f"🔧 Calling {tool_name} with parameters: {list(parameters.keys())}")
            response = call_tool(tool_name, parameters)
            return format_confluence_response(tool_name, response, tool_call.get("original_query"), action)
       
        

    except Exception as e:
        if Config.DEBUG:
            import traceback
            logger.debug(f"🐛 Full traceback: {traceback.format_exc()}")
        return f"❌ Unexpected error: {str(e)}" 