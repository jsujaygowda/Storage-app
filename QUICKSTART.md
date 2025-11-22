# Quick Start Guide - Excel Difference Finder

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage Examples

### CLI Version (Recommended for Automation)

#### Basic Comparison
```bash
python excel_diff_cli.py file1.xlsx file2.xlsx
```

#### With Output File
```bash
python excel_diff_cli.py file1.xlsx file2.xlsx -o differences.xlsx
```

#### Compare Specific Sheets
```bash
python excel_diff_cli.py file1.xlsx file2.xlsx -s1 "Sheet1" -s2 "Sheet2"
```

#### Using Key Columns (Best for files with unique IDs)
```bash
python excel_diff_cli.py file1.xlsx file2.xlsx -k "ID" "Employee_ID"
```

#### Using the Helper Script
```bash
./run_cli.sh file1.xlsx file2.xlsx -o output.xlsx
```

### Web Application (Interactive)

```bash
streamlit run excel_comparator.py
```

Then open your browser to `http://localhost:8501`

## Output File Structure

The output Excel file contains multiple sheets:

1. **Summary** - Overview statistics
2. **Column_Differences** - Columns only in one file
3. **Cell_Differences** - Cell-by-cell differences
4. **Only_in_File1** - Rows only in first file
5. **Only_in_File2** - Rows only in second file
6. **Modified_Rows_File1** - Complete rows from file1 with differences
7. **Modified_Rows_File2** - Complete rows from file2 with differences

## Comparison Methods

### Position-Based (Default)
- Compares rows by position
- Good for files with same structure and order

### Key-Based (-k option)
- Compares rows by key columns
- Better for files with different row orders
- More accurate for identifying changes

## Tips

1. Use key columns when your files have unique identifiers (IDs)
2. Ensure column headers match for best results
3. For large files, the comparison may take a few moments
4. The output file is automatically created with a timestamp if not specified

