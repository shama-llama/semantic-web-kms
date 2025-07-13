#!/bin/bash

BASE_URL=${1:-"http://localhost:5000"}
API_ENDPOINTS=(
    "/api/health"
    "/api/dashboard_stats"
    "/api/repositories"
    "/api/organizations"
)

echo "Performance Testing for Semantic Web KMS API"
echo "Base URL: $BASE_URL"
echo "=========================================="

for endpoint in "${API_ENDPOINTS[@]}"; do
    echo "Testing $endpoint..."
    
    # Test response time
    start_time=$(date +%s.%N)
    response=$(curl -s -w "%{http_code}" -o /tmp/response.json "$BASE_URL$endpoint")
    end_time=$(date +%s.%N)
    
    # Calculate response time
    response_time=$(echo "$end_time - $start_time" | bc -l)
    response_time_ms=$(echo "$response_time * 1000" | bc -l)
    
    # Check if response was successful
    if [ "$response" = "200" ]; then
        status="SUCCESS"
    else
        status="FAILED (HTTP $response)"
    fi
    
    echo "  Status: $status"
    echo "  Response Time: ${response_time_ms}ms"
    
    # Show response size if successful
    if [ "$response" = "200" ]; then
        response_size=$(wc -c < /tmp/response.json)
        echo "  Response Size: ${response_size} bytes"
    fi
    
    echo ""
done

# Clean up
rm -f /tmp/response.json

echo "Performance test completed!" 