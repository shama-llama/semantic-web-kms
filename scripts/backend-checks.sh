#!/bin/bash

# Uncomment 'set -e' to allow the script to stop on errors
# set -e

echo "Running backend checks..."
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

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

print_header() {
    echo -e "${BOLD}${CYAN}$1${NC}"
}

print_step() {
    echo -e "${PURPLE}→${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    print_status "Activating virtual environment..."
    source .venv/bin/activate
else
    print_warning "No virtual environment found. Please run: python3 -m venv .venv"
    exit 1
fi

# Install dependencies if needed
print_status "Installing backend dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pytest pytest-cov flake8 mypy black isort pydocstyle vulture pyright build

# Initialize results tracking
declare -A CHECK_RESULTS

# Build step
echo ""
print_header "BUILD CHECKS"
print_step "Running build checks..."

print_status "Checking if package can be built..."
if python -m build; then
    print_success "Package build successful"
    CHECK_RESULTS[build]="SUCCESS"
else
    print_error "Package build failed"
    CHECK_RESULTS[build]="FAIL"
fi

# Quick linting checks
echo ""
print_header "LINTING CHECKS"
print_step "Running quick linting checks..."

print_status "Running black check..."
if black --check app/; then
    print_success "black passed"
    CHECK_RESULTS[black]="SUCCESS"
else
    print_error "black failed - run: black app/"
    CHECK_RESULTS[black]="FAIL"
fi

print_status "Running isort check..."
if isort --check-only app/; then
    print_success "isort passed"
    CHECK_RESULTS[isort]="SUCCESS"
else
    print_error "isort failed - run: isort app/"
    CHECK_RESULTS[isort]="FAIL"
fi

print_status "Running flake8..."
if flake8 app/; then
    print_success "flake8 passed"
    CHECK_RESULTS[flake8]="SUCCESS"
else
    print_error "flake8 failed"
    CHECK_RESULTS[flake8]="FAIL"
fi

print_status "Running mypy..."
if mypy app/; then
    print_success "mypy passed"
    CHECK_RESULTS[mypy]="SUCCESS"
else
    print_error "mypy failed"
    CHECK_RESULTS[mypy]="FAIL"
fi

# Quick tests
echo ""
print_header "BACKEND TESTS"
print_step "Running backend tests..."
if pytest --cov=app --cov-report=term-missing; then
    print_success "Backend tests passed"
    CHECK_RESULTS[backend_tests]="SUCCESS"
else
    print_error "Backend tests failed"
    CHECK_RESULTS[backend_tests]="FAIL"
fi

echo ""
print_header "FINAL SUMMARY"
for check in "${!CHECK_RESULTS[@]}"; do
    result=${CHECK_RESULTS[$check]}
    if [ "$result" == "SUCCESS" ]; then
        print_success "$check"
    else
        print_error "$check"
    fi
done
echo ""
print_status "Checks complete. Review the summary above for any failures." 