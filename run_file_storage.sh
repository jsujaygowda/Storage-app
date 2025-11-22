#!/bin/bash

# File Storage & Management App - Launch Script
echo "🚀 Starting File Storage & Management App..."
echo "📦 Checking dependencies..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import streamlit; import pandas" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
fi

echo "✅ Dependencies ready!"
echo "🌐 Launching the application..."
echo "📱 The app will open in your default web browser"
echo "🔗 If it doesn't open automatically, go to: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Run the Streamlit app
streamlit run file_storage_app.py

