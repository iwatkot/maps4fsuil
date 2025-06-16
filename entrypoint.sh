#!/bin/bash

echo "======================================"
echo "   maps4FS Docker Container Startup   "
echo "======================================"
echo "Date: $(date)"
echo "User: $(whoami)"
echo "Working Directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Uvicorn version: $(uvicorn --version)"
echo "Streamlit version: $(streamlit --version)"
echo "PYTHONPATH: $PYTHONPATH"
echo "--------------------------------------"
echo "Starting FastAPI (Uvicorn) on port 8000..."
echo "Starting Streamlit UI on port 8501..."
echo "======================================"

uvicorn maps4fsapi.main:app --host 0.0.0.0 --port 8000 &
streamlit run ./maps4fsui/ui.py --server.port 8501