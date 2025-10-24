#!/bin/bash

# Script to clean up files before committing to git
# Run this script to remove temporary and generated files

echo "🧹 Cleaning up files before commit..."
echo "=" * 60

# Remove Python cache files
echo "Removing Python cache files..."
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove pytest cache
echo "Removing pytest cache..."
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Remove coverage files
echo "Removing coverage files..."
find . -type f -name ".coverage*" -delete
find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

# Remove build artifacts
echo "Removing build artifacts..."
rm -rf build/ dist/ *.egg-info

# Remove temporary files
echo "Removing temporary files..."
find . -type f -name "*~" -delete
find . -type f -name "*.bak" -delete
find . -type f -name ".DS_Store" -delete

# List remaining files in examples
echo ""
echo "✅ Cleanup complete!"
echo ""

echo ""
echo "📊 Git status:"
git status --short

echo ""
echo "✨ Ready to commit!"
