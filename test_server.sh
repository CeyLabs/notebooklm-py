#!/bin/bash
# Test script for NotebookLM API server
# Usage: ./test_server.sh [base_url] [api_key]

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
API_KEY="${2:-${API_SECRET_KEY}}"

if [ -z "$API_KEY" ]; then
    echo "Error: API key not provided"
    echo "Usage: $0 [base_url] [api_key]"
    echo "Or set API_SECRET_KEY environment variable"
    exit 1
fi

echo "Testing NotebookLM API at $BASE_URL"
echo "======================================="

# Test 1: Health check
echo -e "\n1. Testing health endpoint..."
HEALTH=$(curl -s "$BASE_URL/health")
echo "Response: $HEALTH"

if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed"
    exit 1
fi

# Test 2: Create notebook
echo -e "\n2. Testing create notebook..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/notebooks/create" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"title": "Test Notebook from API"}')

echo "Response: $CREATE_RESPONSE"

if echo "$CREATE_RESPONSE" | grep -q "notebook_id"; then
    NOTEBOOK_ID=$(echo "$CREATE_RESPONSE" | grep -o '"notebook_id":"[^"]*"' | cut -d'"' -f4)
    echo "✓ Notebook created: $NOTEBOOK_ID"
else
    echo "✗ Failed to create notebook"
    echo "Response: $CREATE_RESPONSE"
    exit 1
fi

# Test 3: Add source
echo -e "\n3. Testing add source..."
SOURCE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/sources/add" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"notebook_id\": \"$NOTEBOOK_ID\", \"url\": \"https://en.wikipedia.org/wiki/Artificial_intelligence\"}")

echo "Response: $SOURCE_RESPONSE"

if echo "$SOURCE_RESPONSE" | grep -q "source_id"; then
    echo "✓ Source added successfully"
else
    echo "✗ Failed to add source"
    echo "Response: $SOURCE_RESPONSE"
    exit 1
fi

echo -e "\n======================================="
echo "All tests passed! ✓"
echo "Notebook ID: $NOTEBOOK_ID"
echo ""
echo "You can view your notebook at:"
echo "https://notebooklm.google.com/notebook/$NOTEBOOK_ID"
