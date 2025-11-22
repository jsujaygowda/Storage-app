#!/bin/bash

# Excel Difference Finder - CLI Launcher
# Usage: ./run_cli.sh file1.xlsx file2.xlsx [options]

echo "🔍 Excel File Difference Finder - CLI"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import pandas" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
fi

# Check if files are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 file1.xlsx file2.xlsx [options]"
    echo ""
    echo "Options:"
    echo "  -o, --output FILE    Specify output file (default: differences_<timestamp>.xlsx)"
    echo "  -s1, --sheet1 NAME   Sheet name in first file"
    echo "  -s2, --sheet2 NAME   Sheet name in second file"
    echo "  -k, --keys COL1 COL2 Key columns for row matching"
    echo ""
    echo "Examples:"
    echo "  $0 file1.xlsx file2.xlsx"
    echo "  $0 file1.xlsx file2.xlsx -o output.xlsx"
    echo "  $0 file1.xlsx file2.xlsx -k ID Name"
    echo ""
    echo "For more help: python3 excel_diff_cli.py --help"
    exit 1
fi

# Run the CLI tool
python3 excel_diff_cli.py "$@"

