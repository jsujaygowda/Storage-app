# Excel Sheet Comparator

A powerful tool for comparing two Excel files and identifying differences between them. Available in two versions:
1. **Web Application (Streamlit)**: Interactive web-based interface with visualizations
2. **Command-Line Interface (CLI)**: Fast, scriptable comparison tool for automation

## Features

- 📊 **Comprehensive Comparison**: Compare two Excel files sheet by sheet
- 🔍 **Multiple Analysis Types**: 
  - Cell-by-cell differences
  - Rows present in only one file
  - Modified rows (rows that exist in both but have differences)
  - Statistical summary of differences
- 📈 **Visual Analytics** (Web App): Interactive charts and graphs showing comparison results
- 📥 **Export Functionality**: Save detailed comparison reports in Excel format with multiple sheets
- 🎯 **Multi-sheet Support**: Select specific sheets from Excel files with multiple sheets
- 🔑 **Key-based Comparison** (CLI): Compare files using key columns for accurate row matching
- ⚙️ **Customizable Options**: Case-sensitive comparison and whitespace handling

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Web Application (Streamlit)

1. Run the application:

```bash
streamlit run excel_comparator.py
```

2. Open your web browser and navigate to the URL shown in the terminal (usually `http://localhost:8501`)

3. Upload your Excel files using the sidebar:
   - Select the first Excel file
   - Select the second Excel file
   - Choose specific sheets if your files contain multiple sheets

4. Click "Compare Files" to start the analysis

5. Review the results:
   - **Summary**: Overview statistics and metrics
   - **Visualizations**: Charts showing comparison results
   - **Cell Differences**: Detailed cell-by-cell differences
   - **File-specific Rows**: Rows that exist in only one file
   - **Export**: Download comprehensive reports

### Command-Line Interface (CLI)

The CLI version is perfect for automation, scripting, and batch processing.

#### Basic Usage

```bash
python excel_diff_cli.py file1.xlsx file2.xlsx
```

This will create a file named `differences_YYYYMMDD_HHMMSS.xlsx` with all the differences.

#### Specify Output File

```bash
python excel_diff_cli.py file1.xlsx file2.xlsx -o output.xlsx
```

#### Compare Specific Sheets

```bash
python excel_diff_cli.py file1.xlsx file2.xlsx -s1 "Sheet1" -s2 "Sheet2"
```

#### Use Key Columns for Row Matching

When your files have unique identifiers (like IDs), use key columns for more accurate comparison:

```bash
python excel_diff_cli.py file1.xlsx file2.xlsx -k "ID" "Employee_ID"
```

#### Get Help

```bash
python excel_diff_cli.py --help
```

#### Output File Structure

The output Excel file contains the following sheets:

- **Summary**: Overview statistics and comparison metrics
- **Column_Differences**: Columns that exist in only one file
- **Cell_Differences**: Detailed cell-by-cell differences
- **Only_in_File1**: Rows that exist only in the first file
- **Only_in_File2**: Rows that exist only in the second file
- **Modified_Rows_File1**: Complete rows from file 1 that have differences
- **Modified_Rows_File2**: Complete rows from file 2 that have differences

## Features in Detail

### Comparison Types

1. **Cell-by-Cell Differences**: Shows exact differences between corresponding cells
2. **Row Differences**: Identifies rows that exist in only one of the files
3. **Statistical Summary**: Provides counts and metrics about the comparison

### Export Options

- Download individual result sheets (cell differences, file-specific rows)
- Download complete comparison report with all results in separate sheets
- All exports are in Excel format for easy analysis

### Visual Analytics

- Pie charts showing distribution of differences
- Bar charts comparing file dimensions
- Interactive Plotly visualizations

## Supported File Formats

- `.xlsx` (Excel 2007+)
- `.xls` (Excel 97-2003)

## Requirements

- Python 3.7+
- pandas
- streamlit
- openpyxl
- xlsxwriter
- plotly
- numpy

## Use Cases

- Data validation and quality assurance
- Version control for spreadsheets
- Audit trails and compliance checking
- Data migration verification
- Report comparison and analysis
- Automated testing and CI/CD pipelines (CLI version)
- Batch processing of multiple file pairs (CLI version)

## Comparison Methods

### Position-Based Comparison (Default)
- Compares rows based on their position in the file
- Best for files with the same structure and order
- Identifies:
  - Rows that differ at the same position
  - Extra rows in either file

### Key-Based Comparison (CLI -k option)
- Compares rows based on key columns (e.g., ID, Employee_ID)
- Best for files where rows may be in different orders
- More accurate for identifying:
  - Added rows (new keys)
  - Removed rows (missing keys)
  - Modified rows (same key, different values)

## Tips for Best Results

1. Ensure both files have similar structure for accurate comparison
2. Use the same column headers in both files when possible
3. Consider data types - the tool converts all data to strings for comparison
4. For large files, the comparison may take a few moments to complete

## Troubleshooting

- **File upload errors**: Ensure files are valid Excel format and not corrupted
- **Empty results**: Check that both files contain data and have compatible structures
- **Performance issues**: For very large files, consider splitting them into smaller chunks

## License

This project is open source and available under the MIT License.
