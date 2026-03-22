#!/bin/bash
# The Convenience Paradox -- Setup Script
# Sets up the development environment for the project.

set -e

echo "=== The Convenience Paradox - Environment Setup ==="

# Check for conda
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda is not installed. Please install Miniconda3 first."
    exit 1
fi

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "ERROR: Ollama is not installed. Run: brew install ollama"
    exit 1
fi

# Create conda environment if it doesn't exist
if conda env list | grep -q "convenience-paradox"; then
    echo "Conda environment 'convenience-paradox' already exists."
else
    echo "Creating conda environment..."
    conda create -n convenience-paradox python=3.12 -y
fi

# Activate and install dependencies
echo "Installing Python dependencies..."
eval "$(conda shell.bash hook)"
conda activate convenience-paradox
pip install -r requirements.txt

# Pull Ollama models
echo "Pulling LLM models (this may take a while)..."
ollama pull qwen3.5:4b
ollama pull qwen3:1.7b

echo ""
echo "=== Setup Complete ==="
echo "To start working:"
echo "  conda activate convenience-paradox"
echo "  ollama serve  (if not running as a service)"
echo "  python -m api.app"
