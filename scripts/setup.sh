#!/bin/bash
set -e

echo "🚀 Setting up Confluence AI Assistant..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]]; then
    print_error "requirements.txt not found. Please run this script from the project root directory."
    exit 1
fi

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
    print_success "Python $python_version is compatible (>= 3.8 required)"
else
    print_error "Python 3.8 or higher is required. Found: $python_version"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Check if Docker is installed and running
print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first:"
    echo "  macOS: brew install docker"
    echo "  Ubuntu: sudo apt-get install docker.io"
    echo "  Windows: Download Docker Desktop from docker.com"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker is installed but not running. Please start Docker and try again."
    exit 1
fi

print_success "Docker is installed and running"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate || {
    print_error "Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

print_success "Python dependencies installed"

# Create config directory if it doesn't exist
if [[ ! -d "config" ]]; then
    print_status "Creating config directory..."
    mkdir -p config
    touch config/__init__.py
fi

# Create .env file if it doesn't exist
if [[ ! -f ".env" ]]; then
    print_status "Creating .env file from template..."
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        print_warning "Please edit .env with your API keys and credentials:"
        echo "  - GOOGLE_API_KEY (from https://makersuite.google.com/app/apikey)"
        echo "  - CONFLUENCE_URL (https://your-domain.atlassian.net/wiki)"
        echo "  - CONFLUENCE_USERNAME (your email)"
        echo "  - CONFLUENCE_API_TOKEN (from https://id.atlassian.com/manage-profile/security/api-tokens)"
    else
        print_error ".env.example not found. Please create it first."
        exit 1
    fi
else
    print_warning ".env file already exists"
fi

# Test MCP Docker image
print_status "Testing MCP Docker image..."
if docker pull ghcr.io/sooperset/mcp-atlassian:latest > /dev/null 2>&1; then
    print_success "MCP Docker image downloaded successfully"
else
    print_error "Failed to download MCP Docker image"
    echo "Please check your internet connection and Docker setup."
    exit 1
fi

# Test Docker run (without credentials)
print_status "Testing Docker container startup..."
if timeout 10s docker run --rm ghcr.io/sooperset/mcp-atlassian:latest --help > /dev/null 2>&1; then
    print_success "MCP Docker container can start successfully"
else
    print_warning "Could not test Docker container startup (this might be normal)"
fi

print_success "✅ Setup completed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env with your API keys and credentials"
echo "2. Test the configuration: ./scripts/test.sh"
echo "3. Run the assistant: python src/main.py"
echo ""
echo "📚 For help getting API keys, see README.md"