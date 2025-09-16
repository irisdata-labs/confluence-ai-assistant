import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.gemini_router import IntelligentGeminiRouter, parse_intent, get_router, health_check


class TestIntelligentGeminiRouter(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config_patcher = patch('src.gemini_router.Config')
        self.mock_config = self.mock_config_patcher.start()
        self.mock_config.GOOGLE_API_KEY = "test_api_key"
        self.mock_config.DEBUG = False
        self.mock_config.validate.return_value = True
        
        self.mock_genai_patcher = patch('src.gemini_router.genai')
        self.mock_genai = self.mock_genai_patcher.start()
        
    def tearDown(self):
        """Clean up after tests"""
        self.mock_config_patcher.stop()
        self.mock_genai_patcher.stop()
        
        # Reset global router instance
        import src.gemini_router
        src.gemini_router._router = None

    @patch('src.gemini_router.genai.configure')
    def test_router_initialization(self, mock_configure):
        """Test router initialization"""
        router = IntelligentGeminiRouter()
        
        self.mock_config.validate.assert_called_once()
        mock_configure.assert_called_once_with(api_key="test_api_key")
        self.assertEqual(router.api_call_count, 0)

    def test_router_initialization_no_api_key(self):
        """Test router initialization fails without API key"""
        self.mock_config.GOOGLE_API_KEY = None
        
        with self.assertRaises(ValueError) as context:
            IntelligentGeminiRouter()
        
        self.assertIn("GOOGLE_API_KEY", str(context.exception))

    @patch('src.gemini_router.genai.GenerativeModel')
    def test_parse_intent_search(self, mock_model_class):
        """Test parsing search intent"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = '{"tool": "confluence_search", "parameters": {"query": "type = page AND title ~ \\"roadmap\\""}}'
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        router = IntelligentGeminiRouter()
        result = router.parse_intent("search for roadmap pages")
        
        self.assertEqual(result["tool"], "confluence_search")
        self.assertIn("query", result["parameters"])
        self.assertEqual(result["original_query"], "search for roadmap pages")
        self.assertEqual(router.api_call_count, 1)

    @patch('src.gemini_router.genai.GenerativeModel')
    def test_parse_intent_get_page(self, mock_model_class):
        """Test parsing get page intent"""
        mock_response = Mock()
        mock_response.text = '{"tool": "confluence_get_page", "parameters": {"title": "Test Page"}}'
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        router = IntelligentGeminiRouter()
        result = router.parse_intent("show me the Test Page")
        
        self.assertEqual(result["tool"], "confluence_get_page")
        self.assertEqual(result["parameters"]["title"], "Test Page")

    @patch('src.gemini_router.genai.GenerativeModel')
    def test_parse_intent_summarize(self, mock_model_class):
        """Test parsing summarize intent"""
        mock_response = Mock()
        mock_response.text = '{"tool": "confluence_search_and_summarize", "parameters": {"query": "type = page AND text ~ \\"docker\\""}}'
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        router = IntelligentGeminiRouter()
        result = router.parse_intent("summarize pages about docker")
        
        self.assertEqual(result["tool"], "confluence_search_and_summarize")
        self.assertIn("docker", result["parameters"]["query"])

    def test_parse_intent_empty_query(self):
        """Test parsing empty query"""
        router = IntelligentGeminiRouter()
        result = router.parse_intent("")
        
        self.assertIn("error", result)
        self.assertIn("Empty query", result["error"])

    @patch('src.gemini_router.genai.GenerativeModel')
    def test_parse_intent_json_decode_error(self, mock_model_class):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.text = "invalid json response"
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        router = IntelligentGeminiRouter()
        result = router.parse_intent("test query")
        
        self.assertIn("error", result)
        self.assertIn("Invalid JSON", result["error"])

    @patch('src.gemini_router.genai.GenerativeModel')
    def test_parse_intent_api_error(self, mock_model_class):
        """Test handling of API errors"""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        
        router = IntelligentGeminiRouter()
        result = router.parse_intent("test query")
        
        self.assertIn("error", result)
        self.assertIn("API error", result["error"])

    def test_clean_response_json_block(self):
        """Test cleaning JSON response with code blocks"""
        router = IntelligentGeminiRouter()
        
        # Test with ```json block
        text = '```json\n{"test": "value"}\n```'
        cleaned = router._clean_response(text)
        self.assertEqual(cleaned, '{"test": "value"}')
        
        # Test with ``` block
        text = '```\n{"test": "value"}\n```'
        cleaned = router._clean_response(text)
        self.assertEqual(cleaned, '{"test": "value"}')

    def test_clean_response_invalid(self):
        """Test cleaning invalid response"""
        router = IntelligentGeminiRouter()
        
        with self.assertRaises(ValueError):
            router._clean_response("not json at all")
        
        with self.assertRaises(ValueError):
            router._clean_response("")

    def test_get_stats(self):
        """Test getting router statistics"""
        router = IntelligentGeminiRouter()
        router.api_call_count = 5
        
        stats = router.get_stats()
        
        self.assertEqual(stats["api_calls_this_session"], 5)
        self.assertEqual(stats["model"], "gemini-1.5-flash")
        self.assertTrue(stats["configured"])

    def test_singleton_get_router(self):
        """Test singleton router pattern"""
        router1 = get_router()
        router2 = get_router()
        
        self.assertIs(router1, router2)

    def test_global_parse_intent(self):
        """Test global parse_intent function"""
        with patch('src.gemini_router.get_router') as mock_get_router:
            mock_router = Mock()
            mock_router.parse_intent.return_value = {"tool": "test"}
            mock_get_router.return_value = mock_router
            
            result = parse_intent("test query")
            
            self.assertEqual(result["tool"], "test")
            mock_router.parse_intent.assert_called_once_with("test query")

    def test_health_check_success(self):
        """Test successful health check"""
        with patch('src.gemini_router.get_router') as mock_get_router:
            mock_get_router.return_value = Mock()
            
            result = health_check()
            self.assertTrue(result)

    def test_health_check_failure(self):
        """Test failed health check"""
        with patch('src.gemini_router.get_router') as mock_get_router:
            mock_get_router.side_effect = Exception("Config error")
            
            result = health_check()
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()