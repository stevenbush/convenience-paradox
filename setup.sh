#!/usr/bin/env bash
# setup.sh — One-step setup for The Convenience Paradox
# Usage: bash setup.sh
# Requires: conda (Miniconda3 or Anaconda) and Ollama (https://ollama.com)

set -e

echo "================================================"
echo " The Convenience Paradox — Environment Setup"
echo "================================================"

# Check conda
if ! command -v conda &>/dev/null; then
  echo "ERROR: conda not found. Install Miniconda3 first: https://docs.conda.io/en/latest/miniconda.html"
  exit 1
fi

# Create conda environment
echo ""
echo "[1/4] Creating conda environment 'convenience-paradox'..."
if conda env list | grep -q "convenience-paradox"; then
  echo "  Environment already exists. Updating..."
  conda env update -f environment.yml --prune
else
  conda env create -f environment.yml
fi

echo ""
echo "[2/4] Verifying Python environment..."
conda run -n convenience-paradox python -c "
import mesa; import flask; import pandas; import plotly; import pydantic
print(f'  mesa        {mesa.__version__}')
print(f'  Flask       {flask.__version__}')
print(f'  pandas      {pandas.__version__}')
print(f'  plotly      {plotly.__version__}')
print(f'  pydantic    {pydantic.__version__}')
print('  All core packages OK.')
"

echo ""
echo "[3/4] Checking Ollama..."
if command -v ollama &>/dev/null; then
  echo "  Ollama found: $(ollama --version 2>/dev/null || echo 'version unknown')"
  echo "  Checking for Qwen 3.5 4B model..."
  if ollama list 2>/dev/null | grep -q "qwen3.5"; then
    echo "  qwen3.5:4b is available."
  else
    echo "  qwen3.5:4b not found. Pull it with: ollama pull qwen3.5:4b"
    echo "  (LLM features will be disabled until the model is available.)"
  fi
else
  echo "  Ollama not found. Install it from https://ollama.com"
  echo "  (LLM features will be disabled; the core simulation dashboard will still work.)"
fi

echo ""
echo "[4/4] Running test suite..."
conda run -n convenience-paradox python -m pytest tests/ -q -k "not ollama" 2>/dev/null && \
  echo "  All tests passed." || echo "  Some tests failed — check output above."

echo ""
echo "================================================"
echo " Setup complete!"
echo ""
echo " To start the dashboard:"
echo "   conda activate convenience-paradox"
echo "   python run.py"
echo "   → Open http://127.0.0.1:5000"
echo ""
echo " For LLM features, also run:"
echo "   ollama serve"
echo "================================================"
