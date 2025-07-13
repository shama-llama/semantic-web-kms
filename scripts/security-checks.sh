#!/bin/bash

# Uncomment 'set -e' to allow the script to stop on errors
# set -e

echo "Running security checks..."
echo "============================="

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

# Backend security checks
echo ""
print_header "BACKEND SECURITY"
print_step "Running backend security checks..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    print_status "Activating virtual environment..."
    source .venv/bin/activate
else
    print_warning "No virtual environment found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Install pip-audit if not already installed
print_status "Installing pip-audit..."
pip install -q pip-audit

# Install bandit if not already installed
print_status "Installing bandit..."
pip install -q bandit

# Results summary associative array
# Requires Bash 4+
declare -A CHECK_RESULTS

print_status "Checking Python dependencies for vulnerabilities with pip-audit..."
if pip-audit; then
    print_success "No security vulnerabilities found in Python dependencies (pip-audit)"
    CHECK_RESULTS[backend_security_pip_audit]="SUCCESS"
else
    print_warning "Security vulnerabilities found in Python dependencies (pip-audit)"
    print_status "Run 'pip-audit' for details"
    CHECK_RESULTS[backend_security_pip_audit]="FAIL"
fi

print_status "Running Bandit static code analysis..."
if bandit -r app/ --quiet; then
    print_success "No issues found by Bandit in backend code"
    CHECK_RESULTS[backend_bandit]="SUCCESS"
else
    print_warning "Potential security issues found by Bandit in backend code"
    print_status "Run 'bandit -r app/' for details"
    CHECK_RESULTS[backend_bandit]="FAIL"
fi

# Frontend security checks
echo ""
print_header "FRONTEND SECURITY"
print_step "Running frontend security checks..."

if [ ! -d "portal" ]; then
    print_error "Portal directory not found"
    CHECK_RESULTS[portal_dir]="FAIL"
else
    CHECK_RESULTS[portal_dir]="SUCCESS"
    cd portal

    # Check Node.js version
    node_version=$(node --version 2>&1 | cut -c2- | cut -d. -f1)
    if [[ "$node_version" -ge "18" ]]; then
        print_success "Node.js version: $(node --version)"
        CHECK_RESULTS[node_version]="SUCCESS"
    else
        print_warning "Node.js version: $(node --version) (recommended: 18+)"
        CHECK_RESULTS[node_version]="FAIL"
    fi

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        if npm ci; then
            print_success "Frontend dependencies installed"
            CHECK_RESULTS[frontend_deps]="SUCCESS"
        else
            print_error "Failed to install frontend dependencies"
            CHECK_RESULTS[frontend_deps]="FAIL"
        fi
    fi

    print_status "Running npm audit..."
    if npm audit --audit-level=moderate; then
        print_success "No moderate or higher vulnerabilities found"
        CHECK_RESULTS[frontend_audit]="SUCCESS"
    else
        print_warning "Vulnerabilities found in npm dependencies"
        print_status "Run 'npm audit' for details"
        CHECK_RESULTS[frontend_audit]="FAIL"
    fi

    print_status "Checking for outdated dependencies..."
    if npm outdated; then
        print_warning "Some dependencies are outdated"
        print_status "Run 'npm outdated' for details"
        CHECK_RESULTS[frontend_outdated]="FAIL"
    else
        print_success "All dependencies are up to date"
        CHECK_RESULTS[frontend_outdated]="SUCCESS"
    fi

    cd ..
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