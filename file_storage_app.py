#!/usr/bin/env python3
"""
File Storage and Management Web Application
A web-based file storage system with organization, search, and access capabilities.
"""

import streamlit as st
import sqlite3
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
import json
import mimetypes
from typing import Optional, List, Dict
import base64
from io import BytesIO
import pandas as pd


# Configuration
STORAGE_DIR = Path("file_storage")
DATABASE_FILE = "file_storage.db"
THUMBNAIL_DIR = STORAGE_DIR / "thumbnails"

# Ensure directories exist
STORAGE_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)


class FileStorageDB:
    """Database manager for file metadata."""
    
    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self.init_database()
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with required tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                file_size INTEGER NOT NULL,
                file_type TEXT,
                file_hash TEXT,
                folder_path TEXT DEFAULT '',
                category TEXT DEFAULT 'Uncategorized',
                tags TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'user'
            )
        """)
        
        # Folders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                parent_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT DEFAULT ''
            )
        """)
        
        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#808080',
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default category
        cursor.execute("""
            INSERT OR IGNORE INTO categories (name, color, description)
            VALUES ('Uncategorized', '#808080', 'Default category for files')
        """)
        
        conn.commit()
        conn.close()
    
    def add_file(self, filename: str, file_path: str, file_size: int, 
                 folder_path: str = '', category: str = 'Uncategorized',
                 description: str = '', tags: List[str] = None) -> int:
        """Add file metadata to database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        file_hash = self._calculate_file_hash(file_path)
        tags_json = json.dumps(tags or [])
        
        cursor.execute("""
            INSERT INTO files (filename, original_filename, file_path, file_size,
                             file_type, file_hash, folder_path, category, tags, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (filename, filename, file_path, file_size, file_type, file_hash,
              folder_path, category, tags_json, description))
        
        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_id
    
    def get_file(self, file_id: int) -> Optional[Dict]:
        """Get file metadata by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_files(self, folder_path: str = None, category: str = None,
                  search_query: str = None, limit: int = None) -> List[Dict]:
        """Get files with optional filters."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM files WHERE 1=1"
        params = []
        
        if folder_path is not None:
            query += " AND folder_path = ?"
            params.append(folder_path)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if search_query:
            query += " AND (filename LIKE ? OR description LIKE ? OR tags LIKE ?)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY uploaded_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_file_access(self, file_id: int):
        """Update file access statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE files 
            SET last_accessed = CURRENT_TIMESTAMP, 
                access_count = access_count + 1
            WHERE id = ?
        """, (file_id,))
        conn.commit()
        conn.close()
    
    def delete_file(self, file_id: int) -> bool:
        """Delete file from database and filesystem."""
        file_info = self.get_file(file_id)
        if not file_info:
            return False
        
        # Delete from filesystem
        file_path = Path(file_info['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()
        
        return True
    
    def create_folder(self, name: str, parent_path: str = '') -> bool:
        """Create a new folder."""
        folder_path = f"{parent_path}/{name}".strip('/')
        if parent_path:
            folder_path = f"{parent_path}/{name}"
        else:
            folder_path = name
        
        # Create physical directory
        full_path = STORAGE_DIR / folder_path
        full_path.mkdir(parents=True, exist_ok=True)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO folders (name, path, parent_path)
                VALUES (?, ?, ?)
            """, (name, folder_path, parent_path))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_folders(self, parent_path: str = '') -> List[Dict]:
        """Get folders in a parent path."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM folders WHERE parent_path = ?
            ORDER BY name
        """, (parent_path,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_categories(self) -> List[Dict]:
        """Get all categories."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def create_category(self, name: str, color: str = '#808080', description: str = '') -> bool:
        """Create a new category."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO categories (name, color, description)
                VALUES (?, ?, ?)
            """, (name, color, description))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def update_file_category(self, file_id: int, category: str):
        """Update file category."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET category = ? WHERE id = ?", (category, file_id))
        conn.commit()
        conn.close()
    
    def update_file_folder(self, file_id: int, folder_path: str):
        """Move file to different folder."""
        file_info = self.get_file(file_id)
        if not file_info:
            return False
        
        old_path = Path(file_info['file_path'])
        new_folder = STORAGE_DIR / folder_path
        new_folder.mkdir(parents=True, exist_ok=True)
        new_path = new_folder / old_path.name
        
        # Move file
        if old_path.exists():
            shutil.move(str(old_path), str(new_path))
        
        # Update database
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE files SET file_path = ?, folder_path = ? WHERE id = ?
        """, (str(new_path), folder_path, file_id))
        conn.commit()
        conn.close()
        
        return True
    
    def get_stats(self) -> Dict:
        """Get storage statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total files
        cursor.execute("SELECT COUNT(*) as count FROM files")
        total_files = cursor.fetchone()['count']
        
        # Total size
        cursor.execute("SELECT SUM(file_size) as total_size FROM files")
        result = cursor.fetchone()
        total_size = result['total_size'] or 0
        
        # Files by category
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM files 
            GROUP BY category
        """)
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Files by type
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN file_type LIKE 'image/%' THEN 'Images'
                    WHEN file_type LIKE 'video/%' THEN 'Videos'
                    WHEN file_type LIKE 'audio/%' THEN 'Audio'
                    WHEN file_type LIKE 'application/pdf' THEN 'PDFs'
                    WHEN file_type LIKE 'application/vnd.ms-excel%' OR file_type LIKE 'application/vnd.openxmlformats-officedocument.spreadsheetml%' THEN 'Spreadsheets'
                    WHEN file_type LIKE 'application/vnd.ms-powerpoint%' OR file_type LIKE 'application/vnd.openxmlformats-officedocument.presentationml%' THEN 'Presentations'
                    WHEN file_type LIKE 'application/msword%' OR file_type LIKE 'application/vnd.openxmlformats-officedocument.wordprocessingml%' THEN 'Documents'
                    WHEN file_type LIKE 'text/%' THEN 'Text Files'
                    ELSE 'Other'
                END as file_group,
                COUNT(*) as count
            FROM files
            GROUP BY file_group
        """)
        by_type = {row['file_group']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'by_category': by_category,
            'by_type': by_type
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""


class FileStorageApp:
    """Main application class."""
    
    def __init__(self):
        self.db = FileStorageDB()
    
    def save_uploaded_file(self, uploaded_file, folder_path: str = '', 
                          category: str = 'Uncategorized', description: str = '',
                          tags: List[str] = None) -> bool:
        """Save uploaded file to storage."""
        try:
            # Create folder if needed
            target_folder = STORAGE_DIR / folder_path if folder_path else STORAGE_DIR
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename if file exists
            file_path = target_folder / uploaded_file.name
            counter = 1
            while file_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                file_path = target_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Add to database
            file_size = file_path.stat().st_size
            self.db.add_file(
                filename=file_path.name,
                file_path=str(file_path),
                file_size=file_size,
                folder_path=folder_path,
                category=category,
                description=description,
                tags=tags or []
            )
            
            return True
        except Exception as e:
            st.error(f"Error saving file: {str(e)}")
            return False
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def get_file_icon(self, file_type: str) -> str:
        """Get emoji icon for file type."""
        if not file_type:
            return "📄"
        
        if file_type.startswith('image/'):
            return "🖼️"
        elif file_type.startswith('video/'):
            return "🎥"
        elif file_type.startswith('audio/'):
            return "🎵"
        elif file_type == 'application/pdf':
            return "📕"
        elif 'excel' in file_type or 'spreadsheet' in file_type:
            return "📊"
        elif 'word' in file_type or 'document' in file_type:
            return "📝"
        elif 'powerpoint' in file_type or 'presentation' in file_type:
            return "📽️"
        elif file_type.startswith('text/'):
            return "📄"
        else:
            return "📦"


def main():
    st.set_page_config(
        page_title="File Storage & Management",
        page_icon="📁",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize app
    if 'app' not in st.session_state:
        st.session_state.app = FileStorageApp()
    
    app = st.session_state.app
    db = app.db
    
    # Sidebar
    st.sidebar.title("📁 File Storage")
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["🏠 Home", "📤 Upload Files", "📂 Browse Files", "🗂️ Organize", "📊 Statistics"]
    )
    
    # Home page
    if page == "🏠 Home":
        st.title("🏠 File Storage & Management System")
        st.markdown("Welcome to your personal file storage system!")
        
        # Statistics cards
        stats = db.get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Files", stats['total_files'])
        with col2:
            st.metric("Total Storage", app.format_file_size(stats['total_size']))
        with col3:
            st.metric("Categories", len(stats['by_category']))
        with col4:
            st.metric("File Types", len(stats['by_type']))
        
        st.markdown("---")
        
        # Recent files
        st.subheader("📋 Recent Files")
        recent_files = db.get_files(limit=10)
        
        if recent_files:
            for file_info in recent_files:
                col1, col2, col3, col4 = st.columns([1, 4, 2, 1])
                with col1:
                    st.write(app.get_file_icon(file_info['file_type']))
                with col2:
                    st.write(f"**{file_info['original_filename']}**")
                    if file_info['description']:
                        st.caption(file_info['description'])
                with col3:
                    st.caption(f"{app.format_file_size(file_info['file_size'])} • {file_info['category']}")
                with col4:
                    if st.button("📥", key=f"download_{file_info['id']}"):
                        file_path = Path(file_info['file_path'])
                        if file_path.exists():
                            db.update_file_access(file_info['id'])
                            with open(file_path, "rb") as f:
                                st.download_button(
                                    label="Download",
                                    data=f.read(),
                                    file_name=file_info['original_filename'],
                                    key=f"dl_{file_info['id']}"
                                )
        else:
            st.info("No files uploaded yet. Upload your first file!")
    
    # Upload page
    elif page == "📤 Upload Files":
        st.title("📤 Upload Files")
        
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            help="You can upload multiple files at once"
        )
        
        if uploaded_files:
            # Organization options
            col1, col2 = st.columns(2)
            
            with col1:
                # Folder selection
                folders = db.get_folders()
                folder_options = [''] + [f['path'] for f in folders]
                selected_folder = st.selectbox("📂 Folder", folder_options)
                
                # Category selection
                categories = db.get_categories()
                category_options = [c['name'] for c in categories]
                selected_category = st.selectbox("🗂️ Category", category_options)
            
            with col2:
                # Tags
                tags_input = st.text_input("🏷️ Tags (comma-separated)", help="e.g., important, work, personal")
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
                
                # Description
                description = st.text_area("📝 Description", height=100)
            
            # Upload button
            if st.button("⬆️ Upload Files", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {uploaded_file.name}...")
                    if app.save_uploaded_file(
                        uploaded_file,
                        folder_path=selected_folder,
                        category=selected_category,
                        description=description,
                        tags=tags
                    ):
                        success_count += 1
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text(f"✅ Successfully uploaded {success_count}/{len(uploaded_files)} files!")
                st.success(f"Upload complete! {success_count} file(s) uploaded successfully.")
                st.rerun()
    
    # Browse page
    elif page == "📂 Browse Files":
        st.title("📂 Browse Files")
        
        # Search and filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_query = st.text_input("🔍 Search files", placeholder="Search by name, description, or tags")
        
        with col2:
            categories = db.get_categories()
            category_filter = st.selectbox("🗂️ Category", ["All"] + [c['name'] for c in categories])
        
        with col3:
            folders = db.get_folders()
            folder_filter = st.selectbox("📂 Folder", ["All"] + [f['path'] for f in folders])
        
        # Get files
        category = category_filter if category_filter != "All" else None
        folder = folder_filter if folder_filter != "All" else None
        files = db.get_files(folder_path=folder, category=category, search_query=search_query)
        
        st.markdown(f"**Found {len(files)} file(s)**")
        st.markdown("---")
        
        # Display files
        if files:
            for file_info in files:
                with st.expander(f"{app.get_file_icon(file_info['file_type'])} {file_info['original_filename']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Size:** {app.format_file_size(file_info['file_size'])}")
                        st.write(f"**Type:** {file_info['file_type']}")
                        st.write(f"**Category:** {file_info['category']}")
                        st.write(f"**Folder:** {file_info['folder_path'] or 'Root'}")
                        if file_info['description']:
                            st.write(f"**Description:** {file_info['description']}")
                        if file_info['tags']:
                            tags = json.loads(file_info['tags'])
                            if tags:
                                st.write(f"**Tags:** {', '.join(tags)}")
                        st.write(f"**Uploaded:** {file_info['uploaded_at']}")
                        st.write(f"**Accessed:** {file_info['access_count']} times")
                    
                    with col2:
                        file_path = Path(file_info['file_path'])
                        if file_path.exists():
                            # Download button
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                                db.update_file_access(file_info['id'])
                                st.download_button(
                                    label="📥 Download",
                                    data=file_data,
                                    file_name=file_info['original_filename'],
                                    key=f"download_{file_info['id']}"
                                )
                            
                            # Delete button
                            if st.button("🗑️ Delete", key=f"delete_{file_info['id']}"):
                                if db.delete_file(file_info['id']):
                                    st.success("File deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete file")
                        else:
                            st.error("File not found")
        else:
            st.info("No files found. Try adjusting your filters or upload some files!")
    
    # Organize page
    elif page == "🗂️ Organize":
        st.title("🗂️ Organize Files")
        
        tab1, tab2, tab3 = st.tabs(["📂 Folders", "🏷️ Categories", "📝 Manage Files"])
        
        with tab1:
            st.subheader("📂 Manage Folders")
            
            # Create folder
            col1, col2 = st.columns(2)
            with col1:
                new_folder_name = st.text_input("New Folder Name")
                parent_folder = st.selectbox("Parent Folder", [""] + [f['path'] for f in db.get_folders()])
            
            with col2:
                st.write("")
                if st.button("➕ Create Folder"):
                    if new_folder_name:
                        if db.create_folder(new_folder_name, parent_folder):
                            st.success(f"Folder '{new_folder_name}' created!")
                            st.rerun()
                        else:
                            st.error("Folder already exists or invalid name")
                    else:
                        st.warning("Please enter a folder name")
            
            # List folders
            st.markdown("### Existing Folders")
            folders = db.get_folders()
            if folders:
                for folder in folders:
                    st.write(f"📂 {folder['path']}")
            else:
                st.info("No folders created yet")
        
        with tab2:
            st.subheader("🏷️ Manage Categories")
            
            # Create category
            col1, col2, col3 = st.columns(3)
            with col1:
                new_category_name = st.text_input("New Category Name")
            with col2:
                category_color = st.color_picker("Color", "#808080")
            with col3:
                st.write("")
                if st.button("➕ Create Category"):
                    if new_category_name:
                        if db.create_category(new_category_name, category_color):
                            st.success(f"Category '{new_category_name}' created!")
                            st.rerun()
                        else:
                            st.error("Category already exists")
                    else:
                        st.warning("Please enter a category name")
            
            # List categories
            st.markdown("### Existing Categories")
            categories = db.get_categories()
            for category in categories:
                st.write(f"🏷️ **{category['name']}** - {category.get('description', '')}")
        
        with tab3:
            st.subheader("📝 Manage Files")
            
            # Get all files
            all_files = db.get_files()
            
            if all_files:
                file_options = {f"{f['original_filename']} (ID: {f['id']})": f['id'] for f in all_files}
                selected_file_label = st.selectbox("Select File", list(file_options.keys()))
                selected_file_id = file_options[selected_file_label]
                
                file_info = db.get_file(selected_file_id)
                
                if file_info:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Change category
                        categories = db.get_categories()
                        new_category = st.selectbox(
                            "Change Category",
                            [c['name'] for c in categories],
                            index=[c['name'] for c in categories].index(file_info['category']) if file_info['category'] in [c['name'] for c in categories] else 0
                        )
                        if st.button("Update Category"):
                            db.update_file_category(selected_file_id, new_category)
                            st.success("Category updated!")
                            st.rerun()
                    
                    with col2:
                        # Move to folder
                        folders = db.get_folders()
                        folder_options = [''] + [f['path'] for f in folders]
                        new_folder = st.selectbox(
                            "Move to Folder",
                            folder_options,
                            index=folder_options.index(file_info['folder_path']) if file_info['folder_path'] in folder_options else 0
                        )
                        if st.button("Move File"):
                            db.update_file_folder(selected_file_id, new_folder)
                            st.success("File moved!")
                            st.rerun()
            else:
                st.info("No files to manage")
    
    # Statistics page
    elif page == "📊 Statistics":
        st.title("📊 Storage Statistics")
        
        stats = db.get_stats()
        
        # Overview
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Files", stats['total_files'])
            st.metric("Total Storage", app.format_file_size(stats['total_size']))
        
        with col2:
            st.metric("Categories", len(stats['by_category']))
            st.metric("File Types", len(stats['by_type']))
        
        st.markdown("---")
        
        # Files by category
        if stats['by_category']:
            st.subheader("📊 Files by Category")
            category_df = pd.DataFrame(list(stats['by_category'].items()), columns=['Category', 'Count'])
            st.bar_chart(category_df.set_index('Category'))
        
        # Files by type
        if stats['by_type']:
            st.subheader("📊 Files by Type")
            type_df = pd.DataFrame(list(stats['by_type'].items()), columns=['Type', 'Count'])
            st.bar_chart(type_df.set_index('Type'))


if __name__ == "__main__":
    main()

