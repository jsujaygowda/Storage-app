# File Storage App - Quick Start Guide

## 🚀 Quick Start

1. **Install dependencies** (if not already installed):
```bash
pip install -r requirements.txt
```

2. **Run the application**:
```bash
streamlit run file_storage_app.py
```

Or use the launch script:
```bash
./run_file_storage.sh
```

3. **Open your browser** to `http://localhost:8501`

## 📋 Basic Workflow

### 1. Upload Files
- Go to **"📤 Upload Files"**
- Select files to upload
- Choose folder and category
- Add tags and description (optional)
- Click "Upload Files"

### 2. Organize Files
- Go to **"🗂️ Organize"**
- Create folders and categories
- Move files between folders
- Change file categories

### 3. Browse Files
- Go to **"📂 Browse Files"**
- Use search to find files
- Filter by category or folder
- Download or delete files

### 4. View Statistics
- Go to **"📊 Statistics"**
- View storage usage
- See files by category and type

## 🗂️ Organization Tips

1. **Folders**: Use for major organization (Work, Personal, Projects)
2. **Categories**: Use for cross-cutting organization (Important, Archive, Draft)
3. **Tags**: Use for flexible searching (urgent, review, final)
4. **Descriptions**: Add context to help remember file contents

## 📁 File Structure

- Files are stored in: `file_storage/` directory
- Database: `file_storage.db` (SQLite)
- Files are organized by folders you create

## 🔍 Search Tips

- Search by filename, description, or tags
- Use filters to narrow down results
- Combine search with category/folder filters

## ⚡ Quick Actions

- **Upload**: Sidebar → Upload Files
- **Browse**: Sidebar → Browse Files
- **Organize**: Sidebar → Organize
- **Stats**: Sidebar → Statistics
- **Home**: Sidebar → Home (recent files)

## 🎯 Key Features

✅ Upload multiple files at once
✅ Organize with folders and categories
✅ Search and filter files
✅ Add tags and descriptions
✅ Track file access history
✅ View storage statistics
✅ Download and delete files
✅ Move files between folders

## 📝 Notes

- Files are stored locally on your machine
- Database is created automatically
- All file metadata is stored in SQLite database
- Files can be accessed from any browser window
- No external cloud services required

## 🔧 Troubleshooting

**Files not showing?**
- Check if upload was successful
- Verify filters are not too restrictive
- Try refreshing the page

**Upload errors?**
- Check disk space
- Verify file permissions
- Check file size limits

**Database errors?**
- Database is auto-created on first run
- Delete `file_storage.db` to reset (files remain)
- Check file permissions

## 🎨 File Type Icons

- 🖼️ Images
- 🎥 Videos
- 🎵 Audio
- 📕 PDFs
- 📊 Spreadsheets
- 📝 Documents
- 📽️ Presentations
- 📄 Text Files
- 📦 Other

Enjoy organizing your files! 🎉

