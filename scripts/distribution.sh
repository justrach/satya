#!/bin/bash
set -e

# Ensure we're in the project root directory
cd "$(dirname "$0")/.."

# Print usage if help is requested
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  echo "Usage: ./scripts/distribution.sh [patch|minor|major]"
  echo ""
  echo "This script automates the release process for the Satya library."
  echo "It will:"
  echo "  1. Bump the version (patch, minor, or major)"
  echo "  2. Generate a changelog"
  echo "  3. Build wheels for the current platform"
  echo "  4. Create a tag and push to GitHub"
  echo ""
  echo "Once complete, the GitHub Actions workflow will:"
  echo "  - Build wheels for all platforms"
  echo "  - Upload wheels to PyPI"
  echo "  - Create a GitHub release"
  echo ""
  echo "Arguments:"
  echo "  patch   Bump the patch version (0.1.0 -> 0.1.1)"
  echo "  minor   Bump the minor version (0.1.0 -> 0.2.0)"
  echo "  major   Bump the major version (0.1.0 -> 1.0.0)"
  exit 0
fi

# Check for clean working directory
if [[ -n $(git status --porcelain) ]]; then
  echo "Error: Working directory is not clean. Please commit or stash changes first."
  exit 1
fi

# Ensure dependencies are installed
echo "Checking for required dependencies..."
pip install --quiet --upgrade pip bump2version wheel
if ! command -v maturin &> /dev/null; then
  echo "Installing maturin..."
  pip install --quiet maturin
fi

# Determine version bump type
VERSION_BUMP=${1:-patch}
if [[ "$VERSION_BUMP" != "patch" && "$VERSION_BUMP" != "minor" && "$VERSION_BUMP" != "major" ]]; then
  echo "Error: Version bump must be 'patch', 'minor', or 'major'."
  echo "Run './scripts/distribution.sh --help' for usage information."
  exit 1
fi

echo "Starting release process with $VERSION_BUMP version bump..."

# Get current version - macOS compatible
CURRENT_VERSION=$(grep 'version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $CURRENT_VERSION"

# Calculate new version manually instead of using bump2version for README.md
if [ "$VERSION_BUMP" == "patch" ]; then
  IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
  NEW_VERSION="$major.$minor.$((patch + 1))"
elif [ "$VERSION_BUMP" == "minor" ]; then
  IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
  NEW_VERSION="$major.$((minor + 1)).0"
elif [ "$VERSION_BUMP" == "major" ]; then
  IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
  NEW_VERSION="$((major + 1)).0.0"
fi
echo "New version: $NEW_VERSION"

# First update pyproject.toml and Cargo.toml
echo "Updating version in pyproject.toml and Cargo.toml..."
# For pyproject.toml
sed -i.bak "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
rm pyproject.toml.bak

# For Cargo.toml
sed -i.bak "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" Cargo.toml
rm Cargo.toml.bak

# Update README.md version manually
echo "Updating version in README.md..."
sed -i.bak "s/Satya is currently in alpha (v[0-9]\+\.[0-9]\+\.[0-9]\+)/Satya is currently in alpha (v$NEW_VERSION)/g" README.md || \
sed -i.bak "s/Satya is currently in alpha (v[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*)/Satya is currently in alpha (v$NEW_VERSION)/g" README.md
rm README.md.bak

# Generate changelog
echo "Generating changelog..."
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")

if [[ "$LATEST_TAG" == "none" ]]; then
  # No tags yet, use all commits
  CHANGELOG=$(git log --pretty=format:"- %s (%h)" --reverse)
else
  # Get commits since last tag
  CHANGELOG=$(git log ${LATEST_TAG}..HEAD --pretty=format:"- %s (%h)" --reverse)
fi

# Write changelog to file
echo "# Changes in v$NEW_VERSION" > CHANGELOG.md
echo "" >> CHANGELOG.md
echo "$CHANGELOG" >> CHANGELOG.md

echo "Changelog generated in CHANGELOG.md"

# Build wheels for current platform
echo "Building wheels for current platform..."
mkdir -p dist
maturin build --release --out dist

echo "Wheels built in ./dist/"

# Commit changes
echo "Committing version bump and changelog..."
git add pyproject.toml Cargo.toml CHANGELOG.md README.md
git commit -m "Bump version to v$NEW_VERSION"

# Create a tag
echo "Creating git tag v$NEW_VERSION..."
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

# Ask for confirmation before pushing
echo ""
echo "Ready to push changes to GitHub."
echo "This will trigger the GitHub Actions workflow to:"
echo "  - Build wheels for all platforms"
echo "  - Publish wheels to PyPI"
echo "  - Create a GitHub Release"
echo ""
read -p "Push changes and tag to GitHub? (y/N) " CONFIRM
if [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]]; then
  echo "Pushing changes and tag to GitHub..."
  git push && git push --tags
  echo ""
  echo "GitHub Actions workflow started!"
  echo "Monitor progress at: https://github.com/$(git remote get-url origin | sed -E 's/.*github.com[:\/](.*)(\.git)?/\1/')/actions"
else
  echo "Changes not pushed. When ready, run:"
  echo "  git push && git push --tags"
  echo ""
  echo "To publish wheels manually (not recommended):"
  echo "  pip install twine"
  echo "  twine upload dist/*"
fi

echo ""
echo "Done! 🎉" 