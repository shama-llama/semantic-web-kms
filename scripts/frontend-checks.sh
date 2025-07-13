#!/bin/bash

# Uncomment 'set -e' to allow the script to stop on errors
# set -e

echo "Running frontend checks..."
echo "==============================="

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
if [ ! -d "portal" ]; then
    print_error "Portal directory not found. Please run from project root."
    exit 1
fi

cd portal

# Results summary associative array
# Requires Bash 4+
declare -A CHECK_RESULTS

# Check Node.js version
node_version=$(node --version 2>&1 | cut -c2- | cut -d. -f1)
if [[ "$node_version" -ge "18" ]]; then
    print_success "Node.js version: $(node --version)"
    CHECK_RESULTS[node_version]="SUCCESS"
else
    print_warning "Node.js version: $(node --version) (recommended: 18+)"
    CHECK_RESULTS[node_version]="FAIL"
fi

# Install dependencies
print_status "Installing frontend dependencies..."
if npm ci; then
    print_success "Frontend dependencies installed"
    CHECK_RESULTS[frontend_deps]="SUCCESS"
else
    print_error "Failed to install frontend dependencies"
    CHECK_RESULTS[frontend_deps]="FAIL"
fi

# Quick linting checks
echo ""
print_header "FRONTEND LINTING"
print_step "Running frontend linting..."
if npm run lint; then
    print_success "Frontend linting passed"
    CHECK_RESULTS[frontend_lint]="SUCCESS"
else
    print_error "Frontend linting failed"
    CHECK_RESULTS[frontend_lint]="FAIL"
fi

# TypeScript type checking
print_status "Running TypeScript type checking..."
if npx tsc --noEmit; then
    print_success "TypeScript type checking passed"
    CHECK_RESULTS[tsc]="SUCCESS"
else
    print_error "TypeScript type checking failed"
    CHECK_RESULTS[tsc]="FAIL"
fi

# Quick tests
echo ""
print_header "FRONTEND TESTS"
print_step "Running frontend tests..."
if npm run test:run; then
    print_success "Frontend tests passed"
    CHECK_RESULTS[frontend_tests]="SUCCESS"
else
    print_error "Frontend tests failed"
    CHECK_RESULTS[frontend_tests]="FAIL"
fi

# Quick build check
echo ""
print_header "FRONTEND BUILD"
print_step "Building frontend..."
if npm run build; then
    print_success "Frontend build successful"
    CHECK_RESULTS[frontend_build]="SUCCESS"
else
    print_error "Frontend build failed"
    CHECK_RESULTS[frontend_build]="FAIL"
fi

cd ..

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