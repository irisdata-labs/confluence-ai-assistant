import unittest
import json
import os
import sys
import subprocess
from unittest.mock import Mock, patch, MagicMock
from src.confluence_client import MCPClient, get_client, call_tool, close_client, health_check

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestMCPClient(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Config
        self.config_patcher = patch('src.confluence_client.Config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.validate.return_value = True
        self.mock_config.get_mcp_command.return_value = [
            "docker", "run", "-i", "--rm", "test-image"
        ]
        
        # Reset global client
        import src.confluence_client
        src.confluence_client._client = None
        
    def tearDown(self):
        """Clean up after tests"""
        self.config_patcher.stop()
        # Reset global client
        import src.confluence_client
        src.confluence_client._client = None

    @patch('src.confluence_client.subprocess.Popen')
    def test_mcp_client_initialization(self, mock_popen):
        """Test MCP client initialization"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # Mock initialization responses
        mock_proc.stdout.readline.side_effect = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "confluence_search"}, {"name": "confluence_get_page"}]}}\n'
        ]
        
        client = MCPClient()
        
        self.mock_config.validate.assert_called_once()
        mock_popen.assert_called_once()
        self.assertEqual(len(client.available_tools), 2)
        self.assertIn("confluence_search", client.available_tools)

    @patch('src.confluence_client.subprocess.Popen')
    def test_mcp_client_docker_not_found(self, mock_popen):
        """Test MCP client handles Docker not found"""
        mock_popen.side_effect = FileNotFoundError("Docker not found")
        
        with self.assertRaises(RuntimeError) as context:
            MCPClient()
        
        self.assertIn("Docker not found", str(context.exception))

    @patch('src.confluence_client.subprocess.Popen')
    def test_send_request_success(self, mock_popen):
        """Test successful request sending"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # We need to provide enough responses for:
        # 1. Initialize call
        # 2. Tools list call (during __init__)
        # 3. Our test call
        responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}\n', 
            '{"jsonrpc": "2.0", "id": 3, "result": {"test": "response"}}\n'
        ]
        
        # Use iter() to create an iterator that gets consumed properly
        mock_proc.stdout.readline.side_effect = iter(responses)
        
        # Initialize client (consumes first 2 responses)
        client = MCPClient()
        
        # Call our test method (consumes 3rd response)
        response = client._send_request("test_method", {"param": "value"})
        
        # Verify response
        self.assertEqual(response["result"]["test"], "response")
        mock_proc.stdin.write.assert_called()
        mock_proc.stdin.flush.assert_called()

    @patch('src.confluence_client.subprocess.Popen')
    def test_send_request_broken_pipe(self, mock_popen):
        """Test handling of broken pipe error"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # Mock initialization
        init_responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}\n'
        ]
        mock_proc.stdout.readline.side_effect = init_responses + [BrokenPipeError()]
        
        client = MCPClient()
        
        # Make stdin.write raise BrokenPipeError
        mock_proc.stdin.write.side_effect = BrokenPipeError("Connection lost")
        
        with self.assertRaises(RuntimeError) as context:
            client._send_request("test_method")
        
        self.assertIn("connection lost", str(context.exception).lower())

    @patch('src.confluence_client.subprocess.Popen')
    def test_call_tool_success(self, mock_popen):
        """Test successful tool calling"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # Mock initialization and tool call response
        init_responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "test_tool"}]}}\n',
            '{"jsonrpc": "2.0", "id": 3, "result": {"content": [{"text": "tool response"}]}}\n'
        ]
        mock_proc.stdout.readline.side_effect = init_responses
        
        client = MCPClient()
        
        # Reset for tool call
        mock_proc.stdout.readline.return_value = '{"jsonrpc": "2.0", "id": 4, "result": {"content": [{"text": "tool response"}]}}\n'
        
        response = client.call_tool("test_tool", {"arg": "value"})
        
        self.assertEqual(response["result"]["content"][0]["text"], "tool response")

    @patch('src.confluence_client.subprocess.Popen')
    def test_call_tool_unavailable(self, mock_popen):
        """Test calling unavailable tool"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # Mock initialization with no tools
        init_responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}\n'
        ]
        mock_proc.stdout.readline.side_effect = init_responses
        
        client = MCPClient()
        
        response = client.call_tool("nonexistent_tool", {})
        
        self.assertIn("error", response)
        self.assertIn("not available", response["error"])

    @patch('src.confluence_client.subprocess.Popen')
    def test_client_close(self, mock_popen):
        """Test client cleanup"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # Mock initialization
        init_responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}\n'
        ]
        mock_proc.stdout.readline.side_effect = init_responses
        
        client = MCPClient()
        client.close()
        
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called()

    @patch('src.confluence_client.subprocess.Popen')
    def test_context_manager(self, mock_popen):
        """Test client as context manager"""
        mock_proc = Mock()
        mock_proc.stdin = Mock()
        mock_proc.stdout = Mock()
        mock_proc.stderr = Mock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        # Mock initialization
        init_responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}}\n',
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}\n'
        ]
        mock_proc.stdout.readline.side_effect = init_responses
        
        with MCPClient() as client:
            self.assertIsNotNone(client)
        
        mock_proc.terminate.assert_called_once()

    @patch('src.confluence_client.MCPClient')
    def test_get_client_singleton(self, mock_client_class):
        """Test singleton client behavior"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        client1 = get_client()
        client2 = get_client()
        
        # Should only create one client instance
        mock_client_class.assert_called_once()
        self.assertIs(client1, client2)

    @patch('src.confluence_client.get_client')
    def test_call_tool_function(self, mock_get_client):
        """Test global call_tool function"""
        mock_client = Mock()
        mock_client.call_tool.return_value = {"result": "success"}
        mock_get_client.return_value = mock_client
        
        response = call_tool("test_tool", {"arg": "value"})
        
        self.assertEqual(response["result"], "success")
        mock_client.call_tool.assert_called_once_with("test_tool", {"arg": "value"})

    @patch('src.confluence_client.get_client')
    def test_call_tool_function_error(self, mock_get_client):
        """Test global call_tool function error handling"""
        mock_get_client.side_effect = Exception("Client error")
        
        response = call_tool("test_tool", {})
        
        self.assertIn("error", response)
        self.assertIn("Client error", response["error"])

    def test_close_client_function(self):
        """Test global close_client function"""
        # Mock global client
        import src.confluence_client
        mock_client = Mock()
        src.confluence_client._client = mock_client
        
        close_client()
        
        mock_client.close.assert_called_once()
        self.assertIsNone(src.confluence_client._client)

    @patch('src.confluence_client.get_client')
    def test_health_check_success(self, mock_get_client):
        """Test successful health check"""
        mock_client = Mock()
        mock_client._send_request.return_value = {"result": {"tools": []}}
        mock_get_client.return_value = mock_client
        
        result = health_check()
        
        self.assertTrue(result)

    @patch('src.confluence_client.get_client')
    def test_health_check_failure(self, mock_get_client):
        """Test failed health check"""
        mock_get_client.side_effect = Exception("Connection error")
        
        result = health_check()
        
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()