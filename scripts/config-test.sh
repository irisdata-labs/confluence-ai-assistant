#!/bin/bash
set -e

echo "🧪 Testing Confluence AI Assistant Configuration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]]; then
    print_error "requirements.txt not found. Please run from project root."
    exit 1
fi

# Check if .env exists
print_status "Checking .env file..."
if [[ ! -f ".env" ]]; then
    print_error ".env file not found. Run ./scripts/setup.sh first."
    exit 1
fi
print_success ".env file exists"

# Check if virtual environment exists and activate it
if [[ -d "venv" ]]; then
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
else
    print_warning "Virtual environment not found, using system Python"
fi

# Test Python imports
print_status "Testing Python dependencies..."
python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    import google.generativeai as genai
    print('✓ google-generativeai imported successfully')
except ImportError as e:
    print('✗ google-generativeai import failed:', e)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print('✓ python-dotenv imported successfully')
except ImportError as e:
    print('✗ python-dotenv import failed:', e)
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    print_success "Python dependencies are working"
else
    print_error "Python dependency test failed"
    exit 1
fi

# Test environment variables
print_status "Testing environment configuration..."
python3 -c "
import os
import sys
from dotenv import load_dotenv

load_dotenv()

required_vars = ['GOOGLE_API_KEY', 'CONFLUENCE_URL', 'CONFLUENCE_USERNAME', 'CONFLUENCE_API_TOKEN']
missing_vars = []

for var in required_vars:
    value = os.getenv(var)
    if not value or value.startswith('your_'):
        missing_vars.append(var)
    else:
        print(f'✓ {var} is configured')

if missing_vars:
    print('✗ Missing or placeholder values for:', ', '.join(missing_vars))
    print('Please update your .env file with real values.')
    sys.exit(1)
else:
    print('✓ All required environment variables are set')
"

if [[ $? -eq 0 ]]; then
    print_success "Environment configuration is complete"
else
    print_error "Environment configuration test failed"
    exit 1
fi

# Test Docker
print_status "Testing Docker connectivity..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running"
    exit 1
fi
print_success "Docker is running"

# Test MCP image
print_status "Testing MCP Docker image..."
if docker image inspect ghcr.io/sooperset/mcp-atlassian:latest > /dev/null 2>&1; then
    print_success "MCP Docker image is available"
else
    print_warning "MCP Docker image not found, attempting to pull..."
    if docker pull ghcr.io/sooperset/mcp-atlassian:latest > /dev/null 2>&1; then
        print_success "MCP Docker image downloaded"
    else
        print_error "Failed to download MCP Docker image"
        exit 1
    fi
fi

# Test Google API connection
print_status "Testing Google API connection..."
python3 -c "
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'config')

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    import google.generativeai as genai
    import os
    
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    
    # Test with a simple request
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content('Hello, this is a test. Please respond with just: API_TEST_SUCCESS')
    
    if 'API_TEST_SUCCESS' in response.text:
        print('✓ Google API connection successful')
    else:
        print('✓ Google API connected but unexpected response')
        
except Exception as e:
    print('✗ Google API test failed:', e)
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    print_success "Google API is working"
else
    print_error "Google API test failed - check your GOOGLE_API_KEY"
    exit 1
fi

# Test basic import of our modules
print_status "Testing project modules..."
python3 -c "
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'config')

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test config
    import settings
    config = settings.Config
    config.validate()
    print('✓ Configuration module works')
    
    # Test router
    import gemini_router
    print('✓ Gemini router module imports')
    
    # Test client
    import confluence_client
    print('✓ Confluence client module imports')
    
    # Test dispatcher
    import dispatcher
    print('✓ Dispatcher module imports')
    
except Exception as e:
    print('✗ Module import failed:', e)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    print_success "All project modules are working"
else
    print_error "Module import test failed"
    exit 1
fi

print_success "🎉 All tests passed!"
echo ""
echo "✅ Your Confluence AI Assistant is ready to use!"
echo ""
echo "🚀 To start the assistant:"
echo "   python src/main.py"
echo ""
echo "📝 Example queries to try:"
echo "   'Find pages about Docker'"
echo "   'Show me the Getting Started page'"
echo "   'Summarize pages containing API'"