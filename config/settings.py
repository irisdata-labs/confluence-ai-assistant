import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration management for Confluence AI Assistant"""
    
    # Google(Gemini) AI Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Confluence MCP Client Configuration
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
    CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
    CONFLUENCE_SPACES_FILTER = os.getenv("CONFLUENCE_SPACES_FILTER", "")
    
    # Docker/MCP Configuration
    MCP_DOCKER_IMAGE = os.getenv("MCP_DOCKER_IMAGE", "ghcr.io/sooperset/mcp-atlassian:latest")
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "8000"))
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "50"))
    
    @classmethod
    def validate(cls):
        """Validate required configuration variables"""
        required_vars = [
            ("GOOGLE_API_KEY", cls.GOOGLE_API_KEY),
            ("CONFLUENCE_URL", cls.CONFLUENCE_URL),
            ("CONFLUENCE_USERNAME", cls.CONFLUENCE_USERNAME),
            ("CONFLUENCE_API_TOKEN", cls.CONFLUENCE_API_TOKEN)
        ]
        
        missing = []
        placeholder = []
        
        for name, value in required_vars:
            if not value:
                missing.append(name)
            elif value.startswith("your_"):  # Detect placeholder values
                placeholder.append(name)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        if placeholder:
            raise ValueError(f"Please replace placeholder values in .env file for: {', '.join(placeholder)}")
        
        return True
    
    @classmethod
    def get_mcp_command(cls):
        """Build MCP Docker command from configuration"""
        return [
            "docker", "run", "-i", "--rm",
            cls.MCP_DOCKER_IMAGE,
            "--confluence-url", cls.CONFLUENCE_URL,
            "--confluence-username", cls.CONFLUENCE_USERNAME,
            "--confluence-token", cls.CONFLUENCE_API_TOKEN
        ]
    
    @classmethod
    def get_debug_info(cls):
        """Get configuration info for debugging (without sensitive data)"""
        return {
            "google_api_configured": bool(cls.GOOGLE_API_KEY),
            "confluence_url": cls.CONFLUENCE_URL,
            "confluence_username": cls.CONFLUENCE_USERNAME,
            "confluence_api_token_configured": bool(cls.CONFLUENCE_API_TOKEN),
            "mcp_docker_image": cls.MCP_DOCKER_IMAGE,
            "debug_mode": cls.DEBUG,
            "max_content_length": cls.MAX_CONTENT_LENGTH,
            "max_search_results": cls.MAX_SEARCH_RESULTS
        }