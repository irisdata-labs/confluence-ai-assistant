import subprocess
import json
import logging
from typing import Dict, List, Optional, Any
from config.settings import Config
import os

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, cmd: Optional[List[str]] = None):
        # Validate configuration first
        Config.validate()
        
        # Use config-based command instead of hardcoded credentials
        if cmd is None:
            cmd = Config.get_mcp_command()
            
        logger.info("🔧 Starting MCP client with Docker...")
        
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except FileNotFoundError:
            raise RuntimeError("Docker not found. Please install Docker to use this tool.")
        except Exception as e:
            raise RuntimeError(f"Failed to start MCP client: {e}")
            
        self.request_id = 0
        self.available_tools: List[str] = []
        self._initialize()

    def _send_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and return the response"""
        self.request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        if params:
            req["params"] = params
            
        request_line = json.dumps(req) + "\n"
        try:
            self.proc.stdin.write(request_line)
            self.proc.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("MCP client connection lost")
        
        # Read response
        response_line = self.proc.stdout.readline()
        if not response_line:
            # Check if process died
            if self.proc.poll() is not None:
                stderr_output = self.proc.stderr.read()
                raise RuntimeError(f"MCP client died: {stderr_output}")
            raise RuntimeError("No response from MCP server")
            
        try:
            return json.loads(response_line)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {response_line}")
            raise RuntimeError(f"Invalid JSON response from MCP server: {e}")

    def _send_notification(self, method: str, params: Optional[Dict] = None) -> None:
        """Send a notification (no response expected)"""
        notif = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notif["params"] = params
            
        notification_line = json.dumps(notif) + "\n"
        try:
            self.proc.stdin.write(notification_line)
            self.proc.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("MCP client connection lost")

    def _initialize(self):
        """Perform MCP initialization handshake"""
        logger.info("🔧 Initializing MCP connection...")
        
        try:
            # Step 1: Initialize
            init_response = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "confluence-ai-assistant",
                    "version": "1.0.0"
                }
            })
            
            if "error" in init_response:
                raise RuntimeError(f"MCP initialization failed: {init_response['error']}")
            
            logger.info("✅ MCP initialized")
            
            # Step 2: Send initialized notification
            self._send_notification("notifications/initialized")
            
            # Step 3: Get available tools
            tools_response = self._send_request("tools/list")
            if "result" in tools_response and "tools" in tools_response["result"]:
                self.available_tools = [tool["name"] for tool in tools_response["result"]["tools"]]
                logger.info(f"✅ Available tools: {', '.join(self.available_tools)}")
            else:
                logger.warning("⚠️ No tools found or error getting tools")
                
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to initialize MCP client: {e}")

    def call_tool(self, name: str, arguments: Dict) -> Dict[str, Any]:
        """Call a tool with the given arguments"""
        if name not in self.available_tools:
            return {"error": f"Tool '{name}' not available. Available tools: {self.available_tools}"}
        
        try:
            response = self._send_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
            return response
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return {"error": f"Failed to call tool {name}: {e}"}

    def close(self) -> None:
        """Close the MCP connection"""
        if hasattr(self, 'proc') and self.proc:
            logger.info("🔒 Closing MCP client...")
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("MCP client didn't terminate gracefully, killing...")
                self.proc.kill()
                self.proc.wait()
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Singleton instance management
_client: Optional[MCPClient] = None

def get_client() -> MCPClient:
    """Get or create the singleton MCP client"""
    global _client
    if _client is None:
        cmd = [
            "docker", "run", "-i", "--rm",
            "ghcr.io/sooperset/mcp-atlassian:latest",
            "--confluence-url", os.environ["CONFLUENCE_URL"],
            "--confluence-username", os.environ["CONFLUENCE_USERNAME"],
            "--confluence-token", os.environ["CONFLUENCE_API_TOKEN"]
        ]
        _client = MCPClient(cmd)
        _client = MCPClient()
    return _client

def call_tool(name: str, arguments: Dict) -> Dict[str, Any]:
    """Call a tool using the singleton client"""
    try:
        client = get_client()
        return client.call_tool(name, arguments)
    except Exception as e:
        logger.error(f"Error in call_tool: {e}")
        return {"error": f"Failed to call tool: {e}"}

def close_client() -> None:
    """Close the singleton client"""
    global _client
    if _client:
        _client.close()
        _client = None

def health_check() -> bool:
    """Check if MCP client is healthy"""
    try:
        client = get_client()
        # Try to list tools as a health check
        response = client._send_request("tools/list")
        return "result" in response
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False