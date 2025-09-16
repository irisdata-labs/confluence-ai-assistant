# 🤖 Confluence AI Assistant

# Confluence AI Assistant

This project builds a bridge between Confluence and AI models that do **not** have native MCP (Model Context Protocol) support — enabling safe, intelligent access to your internal knowledge base.

---

## Why this exists

- **Non-Claude readiness**: Claude comes with MCP servers built in, making it easy to plug in tools. Gemini, ChatGPT, and many others **currently lack** this built-in support.  
- This assistant fills that gap by providing a custom MCP client + router so you can use those models with Confluence via MCP.

---

## What it does

- Allows queries like search, summarization, or finding pages in Confluence via prompt.  
- Supports preset or custom prompts.  
- Runs locally (via Docker) or deployed, using environment variables for your Confluence credentials.

---

## What it *doesn’t* do (intentionally)

- It does **not** expose tools to create, edit, or delete Confluence pages.  
- Why:

  1. **Read/search/summarize benefit from LLM intelligence** — interpreting natural language, fetching content, summarizing context are where LLMs shine.  
  2. **Create/delete/edit are deterministic operations** — they can be coded directly via APIs without language interpretation.  
  3. **Risk of misinterpretation** — LLMs may misjudge intent, which in destructive actions (delete, overwrite) could be harmful.

---

## Safety & scope

- Only non-destructive actions (read, search, summarize) are exposed via the MCP tools.  
- All sensitive operations (like page creation or deletion) are left out to reduce risk.  
- Credential management and config are via environment variables, no hardcoded secrets (especially for tokens).

---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

## ✨ Features

- 🤖 **Natural Language Processing**: Use Google Gemini AI to understand complex queries
- 🔍 **Intelligent Search**: Automatically generates optimal Confluence CQL queries
- 📄 **Content Operations**: Retrieve, create, update, and delete Confluence pages
- 📊 **Smart Summarization**: AI-powered content summaries for pages and search results
- 🏗️ **Multi-step Operations**: Chains operations intelligently (search → get → summarize)
- 🎯 **Context-Aware**: Understands intent beyond keywords (view vs search vs summarize)
- 🔐 **Secure**: Environment-based configuration, no hardcoded credentials
- 🐳 **Docker-based MCP**: Uses containerized Confluence client for reliability

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Docker (for MCP Confluence client)
- Google Gemini API key
- Confluence API token

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/confluence-ai-assistant.git
cd confluence-ai-assistant

# 2. Run setup script (or manual steps below)
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials (see Configuration section)

# 4. Run the assistant
python src/main.py
```

### Manual Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Pull the MCP Docker image
docker pull ghcr.io/sooperset/mcp-atlassian:latest

# Create and configure .env file
cp .env.example .env
```

## ⚙️ Configuration

Create a `.env` file with your credentials:

```env
# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Confluence Configuration
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@domain.com
CONFLUENCE_TOKEN=your_confluence_api_token

MCP_DOCKER_IMAGE=ghcr.io/sooperset/mcp-atlassian:latest

# Optional Settings
DEBUG=false
MAX_CONTENT_LENGTH=8000
MAX_SEARCH_RESULTS=50
CONFLUENCE_SPACES_FILTER=
```

### Getting API Keys

#### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the generated key to `GEMINI_API_KEY`

#### Confluence API Token
1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Copy the token to `CONFLUENCE_TOKEN`
4. Use your Confluence email as `CONFLUENCE_USERNAME`

## 💬 Usage Examples

### Interactive Mode (run from the project root)

```bash
python -m src.main 
```

Then use natural language:

```
You: Find pages about Docker
🤖 Assistant: 🔍 Found 5 pages containing Docker, showing 5:

1. **Docker Setup Guide** (Space: Engineering, ID: 12345)
   📄 Complete guide for setting up Docker in development...
   🔗 https://yourcompany.atlassian.net/wiki/...

You: Summarize the Docker Setup Guide
🤖 Assistant: 📋 Summary of Docker Setup Guide (Space: Engineering)

This guide provides comprehensive instructions for setting up Docker
in development environments, including installation steps for various
operating systems, configuration best practices, and troubleshooting
common issues...
```

### Command Examples

| Intent | Example Query | What It Does |
|--------|---------------|-------------|
| **Search** | "Find pages about API documentation" | Searches for pages containing "API documentation" |
| **Get Content** | "Show me the 'Getting Started' page" | Retrieves and displays specific page content |
| **Summarize Page** | "Summarize the Docker guide" | Gets page and creates AI summary |
| **Summarize Search** | "Overview of all pages mentioning security" | Searches and summarizes multiple pages |
| **Space Overview** | "Executive summary of Engineering space" | Analyzes entire space and creates overview |
| **List Pages** | "List all pages in Product space" | Shows all pages in a specific space |

### Advanced Queries

```
# Multi-word phrase handling
"Show me pages containing IT access"  # Searches as exact phrase using Confluence smart siteSearch 

# Space-specific searches  
"Find roadmap pages in Product_Updates space"

# Title vs content distinction
"Search for pages titled roadmap"  # Searches titles only
"Find pages mentioning roadmap"     # Searches full content

# Complex operations
"Give me a summary of all authentication-related pages"
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   User Input    │───▶│ Gemini AI    │───▶│ Intent & CQL    │
│ Natural Language│    │ Router       │    │ Generation      │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                     │
                                                     ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Formatted       │◀───│ Response     │◀───│ MCP Confluence  │
│ Response        │    │ Formatter    │    │ Client (Docker) │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

### Key Components

- **Gemini Router** (`gemini_router.py`): Converts natural language to structured commands
- **Dispatcher** (`dispatcher.py`): Orchestrates multi-step operations and formatting
- **MCP Client** (`confluence_client.py`): Secure Docker-based Confluence client
- **Main** (`main.py`): Interactive CLI interface

## 🧪 Development

### Project Structure

```
confluence-ai-assistant/
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI interface
│   ├── gemini_router.py        # AI intent parsing
│   ├── dispatcher.py           # Operation orchestration
│   └── confluence_client.py    # MCP client wrapper
├── config/
│   └── settings.py             # Configuration management
├── tests/
│   ├── test_gemini_router.py
│   ├── test_dispatcher.py
│   └── fixtures/
├── docs/
├── scripts/
│   └── setup.sh
├── .env.example
├── requirements.txt
└── README.md
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Code formatting
black src/
flake8 src/
```

### Adding New Features

1. **New Operations**: Add to `dispatcher.py` and update Gemini prompt
2. **New Tools**: Extend MCP client in `confluence_client.py`
3. **Response Formats**: Modify formatters in `dispatcher.py`

## 🛠️ Troubleshooting

### Common Issues

**Docker not found**
```bash
# Install Docker first
# macOS: brew install docker
# Ubuntu: apt-get install docker.io
# Windows: Download Docker Desktop
```

**MCP client fails to start**
```bash
# Test Docker connectivity
docker run --rm hello-world

# Check if MCP image is available
docker pull ghcr.io/sooperset/mcp-atlassian:latest
```

**Gemini API errors**
```bash
# Verify API key
echo $GEMINI_API_KEY

# Test API access
curl -H "x-goog-api-key: $GEMINI_API_KEY" \
     https://generativelanguage.googleapis.com/v1/models
```

**Confluence connection issues**
- Verify your Confluence URL format: `https://domain.atlassian.net/wiki`
- Ensure API token has proper permissions
- Check if your account has access to the spaces you're querying

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
python -m src.main
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/confluence-ai-assistant.git
cd confluence-ai-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Run tests
pytest
```

### Pull Request Process

1. Create a feature branch
2. Make your changes with tests
3. Ensure all tests pass
4. Update documentation
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Google Gemini AI](https://deepmind.google/technologies/gemini/) for intelligent language processing
- [MCP Atlassian](https://github.com/sooperset/mcp-atlassian) for Confluence integration
- [Model Context Protocol](https://modelcontextprotocol.io/) for standardized AI tool integration

## 🔗 Related Projects

- [MCP Atlassian](https://github.com/sooperset/mcp-atlassian) - The underlying Confluence MCP server
- [Claude Desktop MCP](https://github.com/anthropics/mcp) - Model Context Protocol specification

## 📞 Support

- 🐛 [Bug Reports](https://github.com/yourusername/confluence-ai-assistant/issues)
- 💡 [Feature Requests](https://github.com/yourusername/confluence-ai-assistant/discussions)
- 📚 [Documentation](https://github.com/yourusername/confluence-ai-assistant/wiki)

---

**Made with ❤️ for better knowledge management**
