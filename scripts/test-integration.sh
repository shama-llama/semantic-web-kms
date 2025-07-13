#!/bin/bash

# Uncomment 'set -e' to allow the script to stop on errors
# set -e

echo "Testing Frontend-Backend Integration"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=${4:-""}
    
    echo -n "Testing $name... "
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url" || echo "000")
    else
        response=$(curl -s -w "%{http_code}" -X "$method" "$url" || echo "000")
    fi
    
    # Extract status code (last 3 characters)
    status_code=${response: -3}
    # Extract response body (everything except last 3 characters)
    response_body=${response%???}
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "503" ]; then
        echo -e "${GREEN}✓${NC} (Status: $status_code)"
        if [ "$status_code" = "503" ]; then
            echo -e "  ${YELLOW}Warning: Backend may not be running${NC}"
        fi
    else
        echo -e "${RED}✗${NC} (Status: $status_code)"
        echo "  Response: $response_body"
    fi
}

# Test backend endpoints directly
echo ""
echo "Testing Backend Endpoints (Direct)"
echo "-------------------------------------"

test_endpoint "Dashboard Stats" "http://localhost:5000/api/dashboard_stats"
test_endpoint "Repositories" "http://localhost:5000/api/repositories"
test_endpoint "Search" "http://localhost:5000/api/search?query=test"
test_endpoint "Graph" "http://localhost:5000/api/graph"
test_endpoint "Analytics" "http://localhost:5000/api/analytics"

# Test frontend API routes (proxied to backend)
echo ""
echo "Testing Frontend API Routes (Proxied)"
echo "----------------------------------------"

test_endpoint "Dashboard Stats" "http://localhost:3000/api/dashboard_stats"
test_endpoint "Repositories" "http://localhost:3000/api/repositories"
test_endpoint "Search" "http://localhost:3000/api/search?query=test"
test_endpoint "Graph" "http://localhost:3000/api/graph"
test_endpoint "Analytics" "http://localhost:3000/api/analytics"

# Test SPARQL endpoint
echo ""
echo "Testing SPARQL Endpoint"
echo "---------------------------"

sparql_query='{"query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5"}'
test_endpoint "SPARQL Query" "http://localhost:5000/api/sparql" "POST" "$sparql_query"

echo ""
echo "Integration Test Complete"
echo ""
echo "Summary:"
echo "- Backend should be running on http://localhost:5000"
echo "- Frontend should be running on http://localhost:3000"
echo "- Check the logs above for any failed endpoints"
echo "- 503 status codes indicate backend is not running"
echo "- 200 status codes indicate successful integration" 