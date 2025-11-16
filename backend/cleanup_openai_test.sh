#!/bin/bash
# Cleanup script for OpenAI testing files
# This removes all testing-related files without touching your main codebase

echo "🧹 Cleaning up OpenAI test files..."

# Count files before deletion
count=0

# Remove test script
if [ -f "test_openai_samples.py" ]; then
    rm test_openai_samples.py
    echo "  ✓ Removed test_openai_samples.py"
    ((count++))
fi

# Remove README
if [ -f "OPENAI_TEST_README.md" ]; then
    rm OPENAI_TEST_README.md
    echo "  ✓ Removed OPENAI_TEST_README.md"
    ((count++))
fi

# Remove this cleanup script (last)
cleanup_script="cleanup_openai_test.sh"

# Remove all generated JSON files
for file in *_test_*.json openai_test_*.json; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✓ Removed $file"
        ((count++))
    fi
done

echo ""
if [ $count -gt 0 ]; then
    echo "✅ Cleaned up $count test file(s)"
else
    echo "ℹ️  No test files found"
fi

# Remove this script last
if [ -f "$cleanup_script" ]; then
    echo "  ✓ Removing cleanup script..."
    rm "$cleanup_script"
fi

echo "✨ Done! Your codebase is clean."

