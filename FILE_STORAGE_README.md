# File Storage & Management System

A web-based file storage and management application built with Streamlit. Store, organize, search, and access your files through an intuitive web interface.

## Features

### 📤 File Upload
- Upload multiple files at once
- Organize files into folders and categories
- Add tags and descriptions to files
- Automatic file type detection

### 📂 File Organization
- **Folders**: Create nested folder structures
- **Categories**: Organize files by category with custom colors
- **Tags**: Add multiple tags to files for easy searching
- **Descriptions**: Add detailed descriptions to files

### 🔍 Search & Browse
- Search files by name, description, or tags
- Filter by category and folder
- View file metadata and statistics
- Access history tracking

### 📊 Statistics & Analytics
- View storage usage statistics
- Files by category breakdown
- Files by type breakdown
- Access count tracking

### 📥 File Management
- Download files
- Delete files
- Move files between folders
- Change file categories
- View file access history

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run file_storage_app.py
```

Or use the launch script:
```bash
./run_file_storage.sh
```

3. Open your browser to `http://localhost:8501`

## Usage

### Uploading Files

1. Navigate to "📤 Upload Files" in the sidebar
2. Select one or more files to upload
3. Choose a folder and category
4. Add tags (comma-separated) and description
5. Click "Upload Files"

### Organizing Files

#### Create Folders
1. Go to "🗂️ Organize" → "📂 Folders"
2. Enter a folder name
3. Select a parent folder (optional)
4. Click "Create Folder"

#### Create Categories
1. Go to "🗂️ Organize" → "🏷️ Categories"
2. Enter a category name
3. Choose a color
4. Add a description (optional)
5. Click "Create Category"

#### Manage Files
1. Go to "🗂️ Organize" → "📝 Manage Files"
2. Select a file from the dropdown
3. Change category or move to different folder
4. Click update buttons to save changes

### Browsing Files

1. Navigate to "📂 Browse Files"
2. Use search bar to find files
3. Filter by category and folder
4. Click on files to view details
5. Download or delete files as needed

### Viewing Statistics

1. Go to "📊 Statistics"
2. View overview metrics
3. See breakdowns by category and file type
4. Monitor storage usage

## File Storage Structure

Files are stored in the `file_storage/` directory, organized by folders. The application uses a SQLite database (`file_storage.db`) to store metadata including:

- File information (name, size, type, path)
- Organization (folder, category, tags)
- Metadata (description, upload date, access history)
- File hash for integrity checking

## Security Notes

- Files are stored locally on your machine
- The database is SQLite (local file)
- No external cloud services are used
- Files are accessible only through the web interface
- Consider adding authentication for production use

## Data Organization

### Default Category
- **Uncategorized**: Default category for files without a specific category

### File Type Detection
The application automatically detects file types and groups them:
- Images (🖼️)
- Videos (🎥)
- Audio (🎵)
- PDFs (📕)
- Spreadsheets (📊)
- Documents (📝)
- Presentations (📽️)
- Text Files (📄)
- Other (📦)

## Tips for Best Results

1. **Use folders** for major organization (e.g., "Work", "Personal", "Projects")
2. **Use categories** for cross-cutting organization (e.g., "Important", "Archive", "Draft")
3. **Add tags** for flexible searching (e.g., "urgent", "review", "final")
4. **Add descriptions** to help remember file contents
5. **Regular cleanup** - delete files you no longer need to save space

## Troubleshooting

### Files not appearing
- Check if files were successfully uploaded
- Verify folder and category filters
- Try refreshing the page

### Upload errors
- Check file size limits
- Ensure sufficient disk space
- Verify file permissions

### Database errors
- The database is automatically created on first run
- If corrupted, delete `file_storage.db` to reset (files will remain)
- Check file permissions on the database file

## File Access

Files can be accessed in multiple ways:
1. **Home page**: View recent files
2. **Browse page**: Search and filter files
3. **Download**: Click download button on any file
4. **Organize page**: Manage file locations and categories

## Storage Location

- **Files**: `file_storage/` directory
- **Database**: `file_storage.db` (SQLite)
- **Thumbnails**: `file_storage/thumbnails/` (future feature)

## Future Enhancements

- User authentication and multi-user support
- File preview functionality
- File versioning
- Cloud storage integration (Google Drive, Dropbox)
- Advanced search with full-text indexing
- File sharing capabilities
- Image thumbnails
- Video/audio playback
- Document preview

## License

This project is open source and available under the MIT License.

