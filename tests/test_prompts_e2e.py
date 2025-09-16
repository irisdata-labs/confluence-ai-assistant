import unittest
import json
import os
import re
from unittest.mock import patch, Mock

# Ensure project root on path if needed by other tests
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.dispatcher import handle_request


def _extract_space_key_from_prompt(prompt: str) -> str:
    # Very lightweight heuristic for space name in prompts
    m = re.search(r"\b([A-Za-z][A-Za-z0-9]{1,15})\b\s+space", prompt, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    # Fallbacks for underscores (not working in some prompts per note)
    m2 = re.search(r"\b([A-Za-z][A-Za-z0-9]+)\b", prompt)
    if m2:
        return m2.group(1)
    return "TEST"


def _extract_title_from_quotes(prompt: str) -> str:
    m = re.search(r"'([^']+)'\s*", prompt)
    if m:
        return m.group(1)
    m2 = re.search(r'"([^"]+)"\s*', prompt)
    if m2:
        return m2.group(1)
    return None


def _extract_id(prompt: str) -> str:
    m = re.search(r"\b(\d{5,})\b", prompt)
    return m.group(1) if m else None


def fake_parse_intent(prompt: str):
    p = prompt.lower()

    # Space executive summary
    if any(k in p for k in ["executive summary", "generate summary of all pages", "summarize the entire", "overview of everything"]):
        return {
            "tool": "confluence_space_summary",
            "parameters": {"space_key": _extract_space_key_from_prompt(prompt)},
            "original_query": prompt,
        }

    # Search-based summarization
    if p.startswith("summarize all pages") or p.startswith("overview of all pages") or p.startswith("give me a summary of pages") or p.startswith("summarize pages"):
        return {
            "tool": "confluence_search_and_summarize",
            "parameters": {"query": f'type = page AND text ~ "{prompt}"'},
            "search_term": prompt,
            "original_query": prompt,
        }

    # Single page summarization (robust patterns)
    if (
        "summarize page" in p
        or "brief overview" in p
        or re.search(r"summarize\s+the\s+contents\s+of\s+page\s+id\s*\d+", p)
        or re.search(r"summary of\s+['\"]", p)
    ):
        page_id = _extract_id(prompt)
        title = _extract_title_from_quotes(prompt)
        params = {"page_id": page_id} if page_id else {"title": title or "Test Page 1"}
        return {
            "tool": "confluence_get_page",
            "parameters": params,
            "action": "summarize_page",
            "original_query": prompt,
        }

    # List pages in space
    if any(k in p for k in ["show all pages in", "list all pages in", "get all pages from", "display all confluence pages in"]):
        return {
            "tool": "confluence_list_pages",
            "parameters": {"space_key": _extract_space_key_from_prompt(prompt)},
            "original_query": prompt,
        }

    # Page retrieval by ID
    if any(k in p for k in ["get page", "show me page id", "display content of page", "view page with id"]) and _extract_id(prompt):
        return {
            "tool": "confluence_get_page",
            "parameters": {"page_id": _extract_id(prompt)},
            "original_query": prompt,
        }

    # Page retrieval by title
    if any(k in p for k in ["get the page titled", "show content of", "display page called", "read the "]) or _extract_title_from_quotes(prompt):
        title = _extract_title_from_quotes(prompt) or prompt.split("titled")[-1].strip() if "titled" in p else "Test Page 1"
        return {
            "tool": "confluence_get_page",
            "parameters": {"title": title},
            "original_query": prompt,
        }

    # Title-specific search
    if any(k in p for k in ["in the title", "with rag in the title", "titled"]):
        return {
            "tool": "confluence_search",
            "parameters": {"query": f'type = page AND title ~ "{prompt}"'},
            "original_query": prompt,
        }

    # Content-specific search or generic search
    if any(k in p for k in ["find pages", "search for", "look for", "show me pages containing"]):
        return {
            "tool": "confluence_search",
            "parameters": {"query": f'type = page AND text ~ "{prompt}"'},
            "original_query": prompt,
        }

    # Default
    return {
        "tool": "confluence_search",
        "parameters": {"query": f'type = page AND text ~ "{prompt}"'},
        "original_query": prompt,
    }


class TestPromptE2E(unittest.TestCase):

    def setUp(self):
        fixtures_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_responses.json')
        with open(fixtures_path, 'r') as f:
            self.sample = json.load(f)

        # Common fixtures
        self.search_response = self.sample["confluence_search_response"]
        self.get_page_response = self.sample["confluence_get_page_response"]

    def _fake_call_tool(self, name, params):
        # Return deterministic fixtures based on tool
        if name == "confluence_search":
            return self.search_response
        if name == "confluence_get_page":
            # Allow title-only direct calls to behave as successful page retrieval
            return self.get_page_response
        # For other tools not directly called here, return a benign default
        return {"result": {"content": [{"text": "[]"}]}}

    @patch('src.dispatcher.summarize_multiple_pages')
    @patch('src.dispatcher.summarize_with_gemini')
    @patch('src.dispatcher.genai.GenerativeModel')
    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    def test_prompt_matrix(self, mock_parse_intent, mock_call_tool, mock_model, mock_summarize, mock_summarize_multiple):
        # Mock intent parser to be deterministic based on prompt
        mock_parse_intent.side_effect = fake_parse_intent

        # Mock tool calls and AI
        mock_call_tool.side_effect = self._fake_call_tool

        # Summarization mocks
        mock_resp = Mock()
        mock_resp.text = "Executive summary placeholder"
        mock_model.return_value.generate_content.return_value = mock_resp
        mock_summarize.return_value = "This is a concise summary."
        mock_summarize_multiple.return_value = "Summary of multiple pages about topic."

        # Test groups
        simple_search_prompts = [
            "Find pages about embeddings",
            "Search for documentation on API endpoints",
            "Look for anything mentioning MCP",
            "Show me pages containing 'IT access'",
        ]

        title_specific_searches = [
            "Find pages with RAG in the title",
            "Search for pages titled Product Roadmap",
            "Look for pages with roadmap in title",
            "Show pages containing server in the title",
        ]

        content_specific_searches = [
            "Find pages with A/b testing in the content",
            "Search for pages containing IT access in body",
            "Look for content mentioning security policies",
        ]

        by_page_id_prompts = [
            "Get page 8421398",
            "Show me page ID 8323384",
            "Display content of page 8356172",
            "View page with ID 8519681",
        ]

        by_title_prompts = [
            "Get the page titled Product Requirements",
            "Show content of 'May Product Roadmap'",
            "Display page called 'April Product Release Notes'",
            "Read the 'RAG Knowledge Base from Confluence' page",
        ]

        list_all_pages_prompts = [
            "Show all pages in Product_Updates space",
            "List all pages in space KnowledgeB",
            "Get all pages from Engineering_Meetings space",
            "Display all confluence pages in DS space",
        ]

        space_filtered_searches = [
            "Find pages about updates in Product_Updates space",
            "Search for meeting notes in Engineering_Meetings space",
            "Look for documentation in KnowledgeB space",
        ]

        single_page_summarization = [
            "Summarize page 8356172",
            "Give me a summary of 'May Product Roadmap'",
            "Summarize the contents of page ID 8356172",
            "Brief overview of the 'Product Requirements' page",
        ]

        search_based_summarization = [
            "Summarize all pages with 'roadmap' in title",
            "Give me a summary of pages containing API documentation",
            "Give me a summary of pages containing API",
            "Summarize pages about machine learning",
            "Overview of all pages mentioning server",
        ]

        space_wide_exec_summary = [
            "Executive summary of ProductUpd space",
            "Generate summary of all pages in KnowledgeB space",
            "Overview of everything in Engineering space",
            "Summarize the entire DS space",
        ]

        # Helper to run and assert
        def assert_found(prompts):
            for pr in prompts:
                with self.subTest(prompt=pr):
                    out = handle_request(pr)
                    # Accept either search results header or single-page card rendering
                    self.assertTrue("Found" in out or out.strip().startswith("📄 **"), msg=f"Unexpected output: {out}")

        def assert_page_result(prompts):
            for pr in prompts:
                with self.subTest(prompt=pr):
                    out = handle_request(pr)
                    self.assertIn("Test Page 1", out)

        def assert_summary(prompts):
            for pr in prompts:
                with self.subTest(prompt=pr):
                    out = handle_request(pr)
                    self.assertTrue("Summary" in out or "Summary of" in out or "Executive" in out or out.strip().startswith("📋 **"), msg=f"Unexpected output: {out}")

        # Execute assertions across categories
        assert_found(simple_search_prompts)
        assert_found(title_specific_searches)
        assert_found(content_specific_searches)
        assert_page_result(by_page_id_prompts)
        assert_page_result(by_title_prompts)
        assert_found(list_all_pages_prompts)
        assert_found(space_filtered_searches)
        assert_summary(single_page_summarization)
        assert_summary(search_based_summarization)
        assert_summary(space_wide_exec_summary)


if __name__ == '__main__':
    unittest.main() 