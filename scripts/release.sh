#!/bin/bash
# Release script for gitlab-pipeline-analyzer
# Usage: ./scripts/release.sh [version]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if version is provided
if [ $# -eq 0 ]; then
    print_error "Version number is required"
    echo "Usage: $0 <version>"
    echo "Example: $0 0.1.1"
    exit 1
fi

VERSION="$1"
TAG="v$VERSION"

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+.*$ ]]; then
    print_error "Invalid version format. Use semantic versioning (e.g., 0.1.1)"
    exit 1
fi

print_status "Starting release process for version $VERSION"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_warning "You are not on the main branch (current: $CURRENT_BRANCH)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Release cancelled"
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_error "You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    print_error "Tag $TAG already exists"
    exit 1
fi

# Update version in pyproject.toml
print_status "Updating version in pyproject.toml"
if command -v sed >/dev/null 2>&1; then
    sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
    rm pyproject.toml.bak
else
    print_error "sed command not found. Please update version manually in pyproject.toml"
    exit 1
fi

# Show the diff
print_status "Version updated. Here's the change:"
git diff pyproject.toml

# Ask for confirmation
read -p "Does this look correct? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Release cancelled"
    git checkout pyproject.toml
    exit 1
fi

# Run tests to make sure everything still works
print_status "Running tests before release..."
if command -v uv >/dev/null 2>&1; then
    uv run pytest --tb=short
else
    python -m pytest --tb=short
fi

if [ $? -ne 0 ]; then
    print_error "Tests failed. Please fix them before releasing."
    git checkout pyproject.toml
    exit 1
fi

print_success "Tests passed!"

# Commit version bump
print_status "Committing version bump"
git add pyproject.toml
git commit -m "chore: bump version to $VERSION"

# Create and push tag
print_status "Creating tag $TAG"
git tag -a "$TAG" -m "Release version $VERSION"

print_status "Pushing changes to remote"
git push origin main
git push origin "$TAG"

print_success "Release $VERSION created successfully!"
print_status "🚀 GitHub Actions will now:"
print_status "  1. Run tests and build the package"
print_status "  2. Automatically publish to PyPI"
print_status "  3. Create a GitHub release"
print_status ""
print_status "Monitor the workflow at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"
