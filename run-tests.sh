#!/bin/bash
# Convenience script to run tests with coverage reporting

set -e

echo "=== Lazy_Bird Test Suite ==="
echo

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Installing test dependencies..."
    pip3 install -r requirements-test.txt
    echo
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"
COVERAGE_MIN="${2:-50}"

case "$TEST_TYPE" in
    unit)
        echo "Running unit tests only..."
        pytest tests/unit -v --cov=scripts --cov=web/backend --cov-report=term-missing --cov-fail-under="$COVERAGE_MIN"
        ;;
    
    integration)
        echo "Running integration tests only..."
        pytest tests/integration -v --cov=scripts --cov=web/backend --cov-report=term-missing --cov-fail-under="$COVERAGE_MIN"
        ;;
    
    e2e)
        echo "Running E2E tests only..."
        pytest tests/e2e -v --cov=scripts --cov=web/backend --cov-report=term-missing --cov-fail-under="$COVERAGE_MIN"
        ;;
    
    all)
        echo "Running all tests..."
        pytest -v --cov=scripts --cov=web/backend \
            --cov-report=html \
            --cov-report=term-missing \
            --cov-report=json \
            --cov-fail-under="$COVERAGE_MIN"
        echo
        echo "Coverage reports generated:"
        echo "  - HTML: htmlcov/index.html"
        echo "  - JSON: coverage.json"
        ;;
    
    quick)
        echo "Running quick test suite (no coverage)..."
        pytest -v -x
        ;;
    
    *)
        echo "Usage: $0 [unit|integration|e2e|all|quick] [min_coverage]"
        echo
        echo "Examples:"
        echo "  $0              # Run all tests with 50% coverage minimum"
        echo "  $0 unit         # Run only unit tests"
        echo "  $0 all 70       # Run all tests with 70% coverage minimum"
        echo "  $0 quick        # Run tests without coverage (fast)"
        exit 1
        ;;
esac

echo
echo "=== Test run complete ==="
