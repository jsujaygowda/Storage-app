#!/bin/bash

# Excel Sheet Comparator - Launch Script
echo "🚀 Starting Excel Sheet Comparator..."
echo "📦 Installing dependencies..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

# Install dependencies
pip3 install -r requirements.txt

echo "✅ Dependencies installed successfully!"
echo "🌐 Launching the application..."
echo "📱 The app will open in your default web browser"
echo "🔗 If it doesn't open automatically, go to: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Run the Streamlit app
streamlit run excel_comparator.py
