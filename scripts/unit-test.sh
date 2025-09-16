#!/bin/bash

# Test runner script for Confluence AI Assistant
# Usage: ./scripts/test.sh [options]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERBOSE=false
COVERAGE=false
SPECIFIC_TEST=""
PATTERN=""

# Help function
show_help() {
    echo "Confluence AI Assistant Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -v, --verbose           Run tests with verbose output"
    echo "  -c, --coverage          Run tests with coverage report"
    echo "  -t, --test TEST_FILE    Run specific test file (e.g., test_gemini_router)"
    echo "  -k, --pattern PATTERN   Run tests matching pattern"
    echo "  --install-deps          Install test dependencies"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all tests"
    echo "  $0 -v                   # Run all tests with verbose output"
    echo "  $0 -c                   # Run tests with coverage"
    echo "  $0 -t test_gemini_router # Run only gemini router tests"
    echo "  $0 -k \"test_parse\"      # Run tests matching 'test_parse'"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -k|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        --install-deps)
            echo -e "${BLUE}Installing test dependencies...${NC}"
            pip install pytest pytest-cov pytest-mock coverage
            echo -e "${GREEN}Dependencies installed successfully!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Function to check if we're in the right directory
check_directory() {
    if [[ ! -f "src/main.py" ]] || [[ ! -d "tests" ]]; then
        echo -e "${RED}Error: Please run this script from the project root directory${NC}"
        echo "Expected structure:"
        echo "  - src/main.py"
        echo "  - tests/"
        exit 1
    fi
}

# Function to check Python environment
check_environment() {
    echo -e "${BLUE}Checking Python environment...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is required but not installed${NC}"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    echo "Python version: $python_version"
    
    # Check if virtual environment is active
    if [[ -z "$VIRTUAL_ENV" ]] && [[ -z "$PIPENV_ACTIVE" ]]; then
        echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
        echo "Consider activating a virtual environment first"
    else
        echo -e "${GREEN}Virtual environment active: ${VIRTUAL_ENV:-$PIPENV_ACTIVE}${NC}"
    fi
}

# Function to install test dependencies if missing
install_test_deps() {
    echo -e "${BLUE}Checking test dependencies...${NC}"
    
    local missing_deps=()
    
    if ! python3 -c "import unittest" 2>/dev/null; then
        missing_deps+=("unittest is built-in but seems broken")
    fi
    
    # Check for optional dependencies
    if ! python3 -c "import pytest" 2>/dev/null; then
        echo -e "${YELLOW}pytest not found (optional but recommended)${NC}"
    fi
    
    if ! python3 -c "import coverage" 2>/dev/null && [[ "$COVERAGE" == true ]]; then
        echo -e "${YELLOW}coverage not found, installing...${NC}"
        pip install coverage
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}Missing dependencies:${NC}"
        printf '%s\n' "${missing_deps[@]}"
        exit 1
    fi
    
    echo -e "${GREEN}All required dependencies available${NC}"
}

# Function to run tests with unittest
run_unittest_tests() {
    local test_args=()
    local test_pattern="test_*.py"
    
    if [[ -n "$SPECIFIC_TEST" ]]; then
        if [[ ! "$SPECIFIC_TEST" == test_* ]]; then
            SPECIFIC_TEST="test_$SPECIFIC_TEST"
        fi
        if [[ ! "$SPECIFIC_TEST" == *.py ]]; then
            SPECIFIC_TEST="$SPECIFIC_TEST.py"
        fi
        test_pattern="$SPECIFIC_TEST"
    fi
    
    echo -e "${BLUE}Running tests with unittest...${NC}"
    echo "Test pattern: $test_pattern"
    
    if [[ "$VERBOSE" == true ]]; then
        test_args+=("-v")
    fi
    
    # Set PYTHONPATH to include project root
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    
    if [[ "$COVERAGE" == true ]]; then
        echo -e "${BLUE}Running with coverage...${NC}"
        python3 -m coverage run --source=src -m unittest discover -s tests -p "$test_pattern" "${test_args[@]}"
        echo ""
        echo -e "${BLUE}Coverage Report:${NC}"
        python3 -m coverage report -m
        python3 -m coverage html -d htmlcov
        echo -e "${GREEN}HTML coverage report generated in htmlcov/${NC}"
    else
        python3 -m unittest discover -s tests -p "$test_pattern" "${test_args[@]}"
    fi
}

# Function to run tests with pytest (if available)
run_pytest_tests() {
    local pytest_args=()
    
    if [[ "$VERBOSE" == true ]]; then
        pytest_args+=("-v")
    fi
    
    if [[ -n "$SPECIFIC_TEST" ]]; then
        if [[ ! "$SPECIFIC_TEST" == test_* ]]; then
            SPECIFIC_TEST="test_$SPECIFIC_TEST"
        fi
        pytest_args+=("tests/$SPECIFIC_TEST.py")
    else
        pytest_args+=("tests/")
    fi
    
    if [[ -n "$PATTERN" ]]; then
        pytest_args+=("-k" "$PATTERN")
    fi
    
    if [[ "$COVERAGE" == true ]]; then
        pytest_args+=("--cov=src" "--cov-report=html" "--cov-report=term-missing")
    fi
    
    echo -e "${BLUE}Running tests with pytest...${NC}"
    python3 -m pytest "${pytest_args[@]}"
}

# Function to check test files exist
check_test_files() {
    local test_files=("test_gemini_router.py" "test_dispatcher.py" "test_confluence_client.py")
    local missing_files=()
    
    for test_file in "${test_files[@]}"; do
        if [[ ! -f "tests/$test_file" ]]; then
            missing_files+=("tests/$test_file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo -e "${RED}Missing test files:${NC}"
        printf '%s\n' "${missing_files[@]}"
        echo ""
        echo "Please create the missing test files or run without the missing modules"
        exit 1
    fi
    
    # Check fixtures
    if [[ ! -f "tests/fixtures/sample_responses.json" ]]; then
        echo -e "${RED}Missing test fixtures: tests/fixtures/sample_responses.json${NC}"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${GREEN}=== Confluence AI Assistant Test Runner ===${NC}"
    echo ""
    
    check_directory
    check_environment
    install_test_deps
    check_test_files
    
    echo ""
    
    # Choose test runner
    if command -v python3 -m pytest --help &> /dev/null && [[ -z "$SPECIFIC_TEST" || "$SPECIFIC_TEST" != *"unittest"* ]]; then
        run_pytest_tests
    else
        run_unittest_tests
    fi
    
    echo ""
    echo -e "${GREEN}=== Tests completed! ===${NC}"
}

# Run main function
main "$@"