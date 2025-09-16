import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.dispatcher import (
    handle_request, format_confluence_response, clean_html_content,
    extract_search_results, extract_page_content, summarize_multiple_pages,
    summarize_with_gemini, handle_space_summary, generate_space_executive_summary
)


class TestDispatcher(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Load sample responses
        fixtures_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_responses.json')
        with open(fixtures_path, 'r') as f:
            self.sample_responses = json.load(f)
    
    def test_clean_html_content(self):
        """Test HTML content cleaning"""
        html_content = "<h1>Title</h1><p>This is a paragraph with <strong>bold</strong> text.</p>"
        expected = "Title\n\nThis is a paragraph with bold text."
        
        result = clean_html_content(html_content)
        
        # Remove extra whitespace for comparison
        result = result.replace('\n\n', '\n').strip()
        expected = expected.replace('\n\n', '\n').strip()
        
        self.assertIn("Title", result)
        self.assertIn("paragraph", result)
        self.assertNotIn("<h1>", result)
        self.assertNotIn("<strong>", result)

    def test_clean_html_content_empty(self):
        """Test cleaning empty HTML content"""
        result = clean_html_content("")
        self.assertEqual(result, "")
        
        result = clean_html_content(None)
        self.assertEqual(result, "")

    def test_extract_search_results(self):
        """Test extracting search results from MCP response"""
        response = self.sample_responses["confluence_search_response"]
        results = extract_search_results(response)
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "123456")
        self.assertEqual(results[0]["title"], "Test Page 1")

    def test_extract_search_results_empty(self):
        """Test extracting from empty response"""
        empty_response = {"result": {"content": []}}
        results = extract_search_results(empty_response)
        
        self.assertEqual(results, [])

    def test_extract_page_content(self):
        """Test extracting page content from MCP response"""
        response = self.sample_responses["confluence_get_page_response"]
        content = extract_page_content(response)
        
        self.assertIsInstance(content, str)
        self.assertIn("Test Page Content", content)
        self.assertIn("<h1>", content)

    def test_extract_page_content_empty(self):
        """Test extracting from empty page response"""
        empty_response = {"result": {"content": []}}
        content = extract_page_content(empty_response)
        
        self.assertEqual(content, "")

    @patch('src.dispatcher.genai.GenerativeModel')
    def test_summarize_with_gemini(self, mock_model_class):
        """Test content summarization with Gemini"""
        mock_response = Mock()
        mock_response.text = "This is a concise summary of the page content."
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        result = summarize_with_gemini("Test Title", "Long content to summarize...")
        
        self.assertEqual(result, "This is a concise summary of the page content.")
        mock_model.generate_content.assert_called_once()

    @patch('src.dispatcher.genai.GenerativeModel')
    def test_summarize_with_gemini_error(self, mock_model_class):
        """Test Gemini summarization error handling"""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        
        result = summarize_with_gemini("Test Title", "Content")
        
        self.assertIn("Error generating summary", result)

    @patch('src.dispatcher.genai.GenerativeModel')
    def test_generate_space_executive_summary(self, mock_model_class):
        """Test space executive summary generation"""
        mock_response = Mock()
        mock_response.text = "Executive Summary:\nThis space contains documentation about testing procedures."
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        pages_data = [
            {"title": "Test Page 1", "excerpt": "Testing procedures"},
            {"title": "Test Page 2", "excerpt": "Quality assurance"}
        ]
        
        result = generate_space_executive_summary(pages_data, "TEST")
        
        self.assertIn("Executive Summary", result)
        mock_model.generate_content.assert_called_once()

    def test_format_confluence_response_error(self):
        """Test formatting error responses"""
        error_response = self.sample_responses["error_response"]
        result = format_confluence_response("confluence_search", error_response)
        
        self.assertIn("Error:", result)
        self.assertIn("not available", result)

    def test_format_confluence_response_search(self):
        """Test formatting search responses"""
        response = self.sample_responses["confluence_search_response"]
        result = format_confluence_response("confluence_search", response, "test query")
        
        self.assertIn("Found 2 page(s)", result)
        self.assertIn("Test Page 1", result)
        self.assertIn("Another Test Page", result)
        self.assertIn("Test Space", result)  # Space name

    def test_format_confluence_response_get_page(self):
        """Test formatting get page responses"""
        response = self.sample_responses["confluence_get_page_response"]
        result = format_confluence_response("confluence_get_page", response)
        
        self.assertIn("Test Page 1", result)
        self.assertIn("Test Space", result)
        self.assertIn("Test Page Content", result)

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    def test_handle_request_search(self, mock_parse_intent, mock_call_tool):
        """Test handling search request"""
        mock_parse_intent.return_value = {
            "tool": "confluence_search",
            "parameters": {"query": "type = page AND title ~ \"test\""},
            "original_query": "search for test pages"
        }
        mock_call_tool.return_value = self.sample_responses["confluence_search_response"]
        
        result = handle_request("search for test pages")
        
        self.assertIn("Found", result)
        mock_parse_intent.assert_called_once_with("search for test pages")
        mock_call_tool.assert_called_once_with("confluence_search", {"query": "type = page AND title ~ \"test\""})

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    def test_handle_request_get_page(self, mock_parse_intent, mock_call_tool):
        """Test handling get page request"""
        mock_parse_intent.return_value = {
            "tool": "confluence_get_page",
            "parameters": {"title": "Test Page 1"},
            "original_query": "show me Test Page"
        }
        mock_call_tool.return_value = self.sample_responses["confluence_get_page_response"]
        
        result = handle_request("show me Test Page")
        
        self.assertIn("Test Page 1", result)
        mock_call_tool.assert_called_once_with("confluence_get_page", {"title": "Test Page 1"})

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    @patch('src.dispatcher.summarize_with_gemini')
    def test_handle_request_summarize(self, mock_summarize, mock_parse_intent, mock_call_tool):
        """Test handling summarization request"""
        mock_parse_intent.return_value = {
            "tool": "confluence_get_page",
            "parameters": {"title": "Test Page 1"},
            "action": "summarize_page",
            "original_query": "summarize Test Page"
        }
        mock_call_tool.return_value = self.sample_responses["confluence_get_page_response"]
        mock_summarize.return_value = "This is a summary of the test page."
        
        result = handle_request("summarize Test Page")
        
        self.assertIn("Summary of Test Page 1", result)
        self.assertIn("This is a summary", result)
        mock_summarize.assert_called_once()

    @patch('src.dispatcher.parse_intent')
    def test_handle_request_parse_error(self, mock_parse_intent):
        """Test handling parse errors"""
        mock_parse_intent.return_value = {"error": "Could not understand request"}
        
        result = handle_request("invalid request")
        
        self.assertIn("Could not understand request", result)

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    def test_handle_request_missing_space_key(self, mock_parse_intent, mock_call_tool):
        """Test handling get page request with missing space key"""
        mock_parse_intent.return_value = {
            "tool": "confluence_get_page",
            "parameters": {"title": "Test Page"},
            "original_query": "show me Test Page"
        }
        
        # Mock search response to find the page
        search_response = {
            "result": {
                "content": [{"text": json.dumps([{"title": "Test Page", "space": {"key": "TEST"}, "id": "123"}])}]
            }
        }
        
        # Mock get page response
        get_page_response = self.sample_responses["confluence_get_page_response"]
        
        mock_call_tool.side_effect = [search_response, get_page_response]
        
        result = handle_request("show me Test Page")
        
        self.assertEqual(mock_call_tool.call_count, 2)
        self.assertIn("Test Page", result)

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    @patch('src.dispatcher.summarize_multiple_pages')
    def test_handle_request_search_and_summarize(self, mock_summarize_multiple, mock_parse_intent, mock_call_tool):
        """Test handling search and summarize request"""
        mock_parse_intent.return_value = {
            "tool": "confluence_search_and_summarize",
            "parameters": {"query": "type = page AND text ~ \"docker\""},
            "search_term": "docker",
            "original_query": "summarize pages about docker"
        }
        mock_call_tool.return_value = self.sample_responses["confluence_search_response"]
        mock_summarize_multiple.return_value = "Summary of multiple pages about docker"
        
        result = handle_request("summarize pages about docker")
        
        self.assertIn("Summary of multiple pages", result)
        mock_summarize_multiple.assert_called_once()

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.summarize_with_gemini')
    def test_summarize_multiple_pages(self, mock_summarize, mock_call_tool):
        """Test summarizing multiple pages"""
        search_results = [
            {"id": "123", "title": "Page 1"},
            {"id": "456", "title": "Page 2"}
        ]
        
        mock_call_tool.return_value = {
            "result": {
                "content": [{"text": json.dumps({"content": "Page content here"})}]
            }
        }
        mock_summarize.return_value = "Page summary"
        
        result = summarize_multiple_pages(search_results, "test")
        
        self.assertIn("Summary of 2 page(s)", result)
        self.assertIn("Page 1", result)
        self.assertIn("Page 2", result)
        self.assertEqual(mock_call_tool.call_count, 2)
        self.assertEqual(mock_summarize.call_count, 2)

    def test_summarize_multiple_pages_empty(self):
        """Test summarizing empty page list"""
        result = summarize_multiple_pages([], "test")
        
        self.assertIn("No pages found", result)

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.generate_space_executive_summary')
    def test_handle_space_summary(self, mock_generate_summary, mock_call_tool):
        """Test handling space summary request"""
        mock_call_tool.return_value = self.sample_responses["confluence_search_response"]
        mock_generate_summary.return_value = "Executive summary of the space"
        
        result = handle_space_summary("TEST")
        
        self.assertIn("Executive Summary for Space 'TEST'", result)
        self.assertIn("Based on analysis of 2 pages", result)
        self.assertIn("Executive summary of the space", result)
        mock_generate_summary.assert_called_once()

    @patch('src.dispatcher.call_tool')
    def test_handle_space_summary_no_pages(self, mock_call_tool):
        """Test handling space summary with no pages"""
        mock_call_tool.return_value = {"result": {"content": [{"text": "[]"}]}}
        
        result = handle_space_summary("EMPTY")
        
        self.assertIn("No pages found in space 'EMPTY'", result)

    @patch('src.dispatcher.call_tool')
    @patch('src.dispatcher.parse_intent')
    def test_handle_request_exception(self, mock_parse_intent, mock_call_tool):
        """Test handling unexpected exceptions"""
        mock_parse_intent.side_effect = Exception("Unexpected error")
        
        result = handle_request("test query")
        
        self.assertIn("Unexpected error", result)


if __name__ == '__main__':
    unittest.main()