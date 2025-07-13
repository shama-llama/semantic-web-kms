#!/bin/bash

# Uncomment 'set -e' to allow the script to stop on errors
# set -e

echo "Running local build and security checks..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
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

# Backend checks
echo ""
print_header "BACKEND CHECKS"
print_step "Running backend checks..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if [[ "$python_version" == "3.12" ]]; then
    print_success "Python version: $(python3 --version)"
else
    print_warning "Python version: $(python3 --version) (recommended: 3.12)"
fi

# Install backend dependencies if needed
if [ ! -d ".venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv .venv
fi

print_status "Activating virtual environment..."
source .venv/bin/activate

print_status "Installing backend dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pytest pytest-cov flake8 mypy black isort pydocstyle vulture pyright pip-audit bandit build

# Results summary associative array
# Requires Bash 4+
declare -A CHECK_RESULTS

# Backend linting checks
echo ""
print_header "BACKEND LINTING"
print_step "Running backend linting checks..."

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

print_status "Running black check..."
if black --check app/; then
    print_success "black passed"
    CHECK_RESULTS[black]="SUCCESS"
else
    print_error "black failed"
    CHECK_RESULTS[black]="FAIL"
fi

print_status "Running isort check..."
if isort --check-only app/; then
    print_success "isort passed"
    CHECK_RESULTS[isort]="SUCCESS"
else
    print_error "isort failed"
    CHECK_RESULTS[isort]="FAIL"
fi

print_status "Running pydocstyle..."
if pydocstyle app/; then
    print_success "pydocstyle passed"
    CHECK_RESULTS[pydocstyle]="SUCCESS"
else
    print_warning "pydocstyle found issues (continuing...)"
    CHECK_RESULTS[pydocstyle]="FAIL"
fi

print_status "Running vulture..."
if vulture app/ --min-confidence 80; then
    print_success "vulture passed"
    CHECK_RESULTS[vulture]="SUCCESS"
else
    print_warning "vulture found potential dead code (continuing...)"
    CHECK_RESULTS[vulture]="FAIL"
fi

print_status "Running pyright..."
if pyright app/; then
    print_success "pyright passed"
    CHECK_RESULTS[pyright]="SUCCESS"
else
    print_error "pyright failed"
    CHECK_RESULTS[pyright]="FAIL"
fi

# Backend tests
echo ""
print_header "BACKEND TESTS"
print_step "Running backend tests..."
if pytest --cov=app --cov=tests --cov-report=term; then
    print_success "Backend tests passed"
    CHECK_RESULTS[backend_tests]="SUCCESS"
else
    print_error "Backend tests failed"
    CHECK_RESULTS[backend_tests]="FAIL"
fi

# Backend build
echo ""
print_header "BACKEND BUILD"
print_step "Building backend package..."
if python -m build; then
    print_success "Backend build successful"
    CHECK_RESULTS[backend_build]="SUCCESS"
else
    print_error "Backend build failed"
    CHECK_RESULTS[backend_build]="FAIL"
fi

# Backend security
echo ""
print_header "BACKEND SECURITY"
print_step "Running backend security checks..."
print_status "Checking Python dependencies for vulnerabilities with pip-audit..."
if pip-audit; then
    print_success "No security vulnerabilities found in Python dependencies (pip-audit)"
    CHECK_RESULTS[backend_security_pip_audit]="SUCCESS"
else
    print_warning "Security vulnerabilities found in Python dependencies (pip-audit)"
    CHECK_RESULTS[backend_security_pip_audit]="FAIL"
fi

print_status "Running Bandit static code analysis..."
if bandit -r app/ --quiet; then
    print_success "No issues found by Bandit in backend code"
    CHECK_RESULTS[backend_bandit]="SUCCESS"
else
    print_warning "Potential security issues found by Bandit in backend code"
    CHECK_RESULTS[backend_bandit]="FAIL"
fi

# Frontend checks
echo ""
print_header "FRONTEND CHECKS"
print_step "Running frontend checks..."

# Check Node.js version
node_version=$(node --version 2>&1 | cut -c2- | cut -d. -f1)
if [[ "$node_version" -ge "18" ]]; then
    print_success "Node.js version: $(node --version)"
    CHECK_RESULTS[node_version]="SUCCESS"
else
    print_warning "Node.js version: $(node --version) (recommended: 18+)"
    CHECK_RESULTS[node_version]="FAIL"
fi

# Check if portal directory exists
if [ ! -d "portal" ]; then
    print_error "Portal directory not found"
    CHECK_RESULTS[portal_dir]="FAIL"
    cd ..
else
    CHECK_RESULTS[portal_dir]="SUCCESS"
    cd portal

    # Install frontend dependencies
    print_status "Installing frontend dependencies..."
    if npm ci; then
        print_success "Frontend dependencies installed"
        CHECK_RESULTS[frontend_deps]="SUCCESS"
    else
        print_error "Failed to install frontend dependencies"
        CHECK_RESULTS[frontend_deps]="FAIL"
    fi

    # Frontend linting
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

    # Frontend tests
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

    # Frontend tests with coverage
    print_step "Running frontend tests with coverage..."
    if npm run test:coverage; then
        print_success "Frontend tests with coverage passed"
        CHECK_RESULTS[frontend_coverage]="SUCCESS"
    else
        print_error "Frontend tests with coverage failed"
        CHECK_RESULTS[frontend_coverage]="FAIL"
    fi

    # Frontend build
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

    # Frontend security
    echo ""
    print_header "FRONTEND SECURITY"
    print_step "Running frontend security checks..."
    print_status "Running npm audit..."
    if npm audit --audit-level=moderate; then
        print_success "No moderate or higher vulnerabilities found"
        CHECK_RESULTS[frontend_audit]="SUCCESS"
    else
        print_warning "Vulnerabilities found in npm dependencies"
        CHECK_RESULTS[frontend_audit]="FAIL"
    fi

    print_step "Checking for outdated dependencies..."
    if npm outdated; then
        print_warning "Some dependencies are outdated"
        CHECK_RESULTS[frontend_outdated]="FAIL"
    else
        print_success "All dependencies are up to date"
        CHECK_RESULTS[frontend_outdated]="SUCCESS"
    fi

    cd ..
fi

echo ""
echo "=============================================="
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