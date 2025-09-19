#!/bin/bash

# Build and upload roundtable-ai package to PyPI

# Activate virtual environment
source ~/.bash_profile && conda activate vibe_cnx

# Install build dependencies if not present
pip install --upgrade build twine

# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build the package
python -m build

# Upload to PyPI (requires proper authentication)
twine upload dist/*