#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting PyPI publication process for satya...${NC}"

# Clean up previous builds
echo -e "${YELLOW}🧹 Cleaning up previous builds...${NC}"
rm -rf dist/ build/ *.egg-info

# Install required packages
echo -e "${YELLOW}📦 Installing build requirements...${NC}"
python -m pip install --upgrade pip
pip install build twine wheel

# Build the package
echo -e "${YELLOW}🔨 Building package...${NC}"
python -m build

# Check the distribution
echo -e "${YELLOW}🔍 Checking distribution...${NC}"
twine check dist/*

# Prompt for PyPI upload
echo -e "${YELLOW}📤 Would you like to upload to PyPI? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
then
    echo -e "${YELLOW}🌐 Uploading to PyPI...${NC}"
    # First try uploading to test PyPI
    echo -e "${YELLOW}📝 Would you like to upload to Test PyPI first? (y/n)${NC}"
    read -r test_response
    
    if [[ "$test_response" =~ ^([yY][eE][sS]|[yY])+$ ]]
    then
        echo -e "${YELLOW}🧪 Uploading to Test PyPI...${NC}"
        python -m twine upload --repository testpypi dist/*
        echo -e "${GREEN}✅ Upload to Test PyPI complete!${NC}"
        echo -e "${YELLOW}🔍 You can check your package at: https://test.pypi.org/project/satya/${NC}"
        
        echo -e "${YELLOW}Would you like to proceed with uploading to production PyPI? (y/n)${NC}"
        read -r prod_response
        
        if [[ ! "$prod_response" =~ ^([yY][eE][sS]|[yY])+$ ]]
        then
            echo -e "${GREEN}✨ Process completed! Package uploaded to Test PyPI only.${NC}"
            exit 0
        fi
    fi
    
    # Upload to production PyPI
    echo -e "${YELLOW}📦 Uploading to production PyPI...${NC}"
    python -m twine upload dist/*
    echo -e "${GREEN}✅ Upload to PyPI complete!${NC}"
    echo -e "${YELLOW}🔍 You can check your package at: https://pypi.org/project/satya/${NC}"
else
    echo -e "${GREEN}✨ Build completed! No files were uploaded to PyPI.${NC}"
fi

echo -e "${GREEN}🎉 Process completed successfully!${NC}" 