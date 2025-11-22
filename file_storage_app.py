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
import zipfile


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
        
        # Users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Migrate existing users table if needed (add is_admin column if it doesn't exist)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            # Column already exists, skip
            pass
        
        # Create default admin user if it doesn't exist
        admin_username = "Admin-Sujay"
        admin_password_hash = self.hash_password("Sjay-admin")
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, is_admin)
            VALUES (?, ?, 1)
        """, (admin_username, admin_password_hash))
        
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
                 description: str = '', tags: List[str] = None, created_by: str = 'user') -> int:
        """Add file metadata to database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        file_hash = self._calculate_file_hash(file_path)
        tags_json = json.dumps(tags or [])
        
        cursor.execute("""
            INSERT INTO files (filename, original_filename, file_path, file_size,
                             file_type, file_hash, folder_path, category, tags, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (filename, filename, file_path, file_size, file_type, file_hash,
              folder_path, category, tags_json, description, created_by))
        
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
    
    # Authentication methods
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username: str, password: str, email: str = None) -> bool:
        """Register a new user."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, is_admin)
                VALUES (?, ?, ?, 0)
            """, (username, password_hash, email))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """Verify user credentials and return user info if valid."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        cursor.execute("""
            SELECT * FROM users WHERE username = ? AND password_hash = ?
        """, (username, password_hash))
        
        row = cursor.fetchone()
        
        if row:
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (row['id'],))
            conn.commit()
            conn.close()
            return dict(row)
        
        conn.close()
        return None
    
    def user_exists(self, username: str) -> bool:
        """Check if username already exists."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def find_duplicate_file(self, original_filename: str, folder_path: str = '') -> Optional[Dict]:
        """Find duplicate file by original filename and folder path."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM files 
            WHERE original_filename = ? AND folder_path = ?
            LIMIT 1
        """, (original_filename, folder_path))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, is_admin, created_at, last_login FROM users ORDER BY username")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user (admin only)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Prevent deleting the default admin
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user and user['username'] == 'Admin-Sujay':
            conn.close()
            return False
        
        try:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False
    
    def update_user_admin_status(self, user_id: int, is_admin: bool) -> bool:
        """Update user admin status (admin only)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Prevent removing admin status from default admin
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user and user['username'] == 'Admin-Sujay':
            conn.close()
            return False
        
        try:
            cursor.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False


class FileStorageApp:
    """Main application class."""
    
    def __init__(self):
        self.db = FileStorageDB()
    
    def save_uploaded_file(self, uploaded_file, folder_path: str = '', 
                          category: str = 'Uncategorized', description: str = '',
                          tags: List[str] = None, created_by: str = 'user', 
                          replace_existing: bool = False):
        """Save uploaded file to storage.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Check for duplicate
            duplicate = self.db.find_duplicate_file(uploaded_file.name, folder_path)
            if duplicate and not replace_existing:
                return False, "duplicate"
            
            # Create folder if needed
            target_folder = STORAGE_DIR / folder_path if folder_path else STORAGE_DIR
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # If replacing, use existing file path; otherwise generate unique filename
            if duplicate and replace_existing:
                file_path = Path(duplicate['file_path'])
                # Delete old file
                if file_path.exists():
                    file_path.unlink()
                # Delete from database
                self.db.delete_file(duplicate['id'])
            else:
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
                tags=tags or [],
                created_by=created_by
            )
            
            return True, "success"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
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
    
    def create_zip_from_files(self, file_ids: List[int], db: FileStorageDB) -> Optional[BytesIO]:
        """Create a zip file from multiple file IDs."""
        zip_buffer = BytesIO()
        
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                added_files = 0
                for file_id in file_ids:
                    file_info = db.get_file(file_id)
                    if file_info:
                        file_path = Path(file_info['file_path'])
                        if file_path.exists():
                            # Use original filename in zip
                            zip_file.write(
                                str(file_path),
                                arcname=file_info['original_filename']
                            )
                            added_files += 1
                            # Update file access
                            db.update_file_access(file_id)
            
            if added_files > 0:
                zip_buffer.seek(0)
                return zip_buffer
            return None
        except Exception as e:
            st.error(f"Error creating zip file: {str(e)}")
            return None


def show_login_page(db: FileStorageDB):
    """Display login/registration page."""
    # Hide sidebar for login page
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            .main > div {
                padding-top: 3rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.title("🔐 File Storage & Management")
        st.markdown("### Welcome! Please login to access your files")
        st.markdown("---")
        
        # Tabs for login and registration
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Login")
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", type="primary", use_container_width=True):
                if login_username and login_password:
                    user = db.verify_user(login_username, login_password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.username = user['username']
                        st.session_state.user_id = user['id']
                        st.session_state.is_admin = bool(user.get('is_admin', 0))
                        st.success(f"Welcome back, {user['username']}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
        
        with tab2:
            st.subheader("Create New Account")
            reg_username = st.text_input("Username", key="reg_username")
            reg_email = st.text_input("Email (optional)", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
            
            if st.button("Register", type="primary", use_container_width=True):
                if not reg_username:
                    st.error("❌ Username is required")
                elif db.user_exists(reg_username):
                    st.error("❌ Username already exists. Please choose a different one.")
                elif not reg_password:
                    st.error("❌ Password is required")
                elif reg_password != reg_confirm_password:
                    st.error("❌ Passwords do not match")
                elif len(reg_password) < 4:
                    st.error("❌ Password must be at least 4 characters long")
                else:
                    if db.register_user(reg_username, reg_password, reg_email if reg_email else None):
                        st.success("✅ Registration successful! Please login.")
                        st.balloons()
                    else:
                        st.error("❌ Registration failed. Please try again.")
        
        st.markdown("---")
        st.caption("💡 Tip: Create an account to start storing and managing your files")


def main():
    # Set page config - must be called before any other streamlit calls
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
    
    # Check authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Show login page if not authenticated
    if not st.session_state.authenticated:
        show_login_page(db)
        return
    
    # Sidebar with logout option
    st.sidebar.title("📁 File Storage")
    
    # Check if user is admin
    is_admin = st.session_state.get('is_admin', False)
    
    # User info and logout
    if 'username' in st.session_state:
        user_display = f"👤 **{st.session_state.username}**"
        if is_admin:
            user_display += " 👑"
        st.sidebar.markdown(user_display)
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_id = None
            st.session_state.is_admin = False
            st.rerun()
    
    st.sidebar.markdown("---")
    
    # Navigation - include admin tab only for admins
    nav_options = ["🏠 Home", "📤 Upload Files", "📂 Browse Files", "🗂️ Organize", "📁 Files Type"]
    if is_admin:
        nav_options.append("👑 User Management")
    
    page = st.sidebar.radio(
        "Navigation",
        nav_options
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
            
            # Check for duplicates before upload
            duplicates = {}
            current_user = st.session_state.get('username', 'user')
            
            for uploaded_file in uploaded_files:
                duplicate = db.find_duplicate_file(uploaded_file.name, selected_folder)
                if duplicate:
                    duplicates[uploaded_file.name] = duplicate
            
            # Show duplicate warning and handle them
            replace_duplicates = False
            if duplicates:
                st.warning(f"⚠️ **{len(duplicates)} duplicate file(s) found!**")
                with st.expander("📋 View Duplicate Files", expanded=True):
                    for filename, dup_info in duplicates.items():
                        st.write(f"📄 **{filename}** (Uploaded: {dup_info['uploaded_at']})")
                
                replace_duplicates = st.checkbox(
                    "✅ Replace duplicate files",
                    help="If checked, duplicate files will be replaced. If unchecked, they will be skipped.",
                    key="replace_duplicates"
                )
            
            # Upload button
            if st.button("⬆️ Upload Files", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                skipped_count = 0
                replaced_count = 0
                error_count = 0
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {uploaded_file.name}...")
                    
                    # Check if duplicate
                    duplicate = db.find_duplicate_file(uploaded_file.name, selected_folder)
                    should_replace = replace_duplicates if duplicate else False
                    
                    # Upload file
                    success, message = app.save_uploaded_file(
                        uploaded_file,
                        folder_path=selected_folder,
                        category=selected_category,
                        description=description,
                        tags=tags,
                        created_by=current_user,
                        replace_existing=should_replace
                    )
                    
                    if success:
                        success_count += 1
                        if duplicate and should_replace:
                            replaced_count += 1
                            st.success(f"✅ **{uploaded_file.name}** uploaded successfully (replaced existing file)!")
                        else:
                            st.success(f"✅ **{uploaded_file.name}** uploaded successfully!")
                    elif message == "duplicate":
                        skipped_count += 1
                        st.info(f"⏭️ **{uploaded_file.name}** skipped - file already exists. Check 'Replace duplicate files' to replace it.")
                    else:
                        error_count += 1
                        st.error(f"❌ **{uploaded_file.name}** failed: {message}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                # Final summary
                status_text.empty()
                progress_bar.empty()
                
                summary_msg = f"**Upload Complete!**\n\n"
                summary_msg += f"✅ Successfully uploaded: **{success_count}** file(s)\n"
                if replaced_count > 0:
                    summary_msg += f"🔄 Replaced: **{replaced_count}** file(s)\n"
                if skipped_count > 0:
                    summary_msg += f"⏭️ Skipped: **{skipped_count}** duplicate file(s)\n"
                if error_count > 0:
                    summary_msg += f"❌ Errors: **{error_count}** file(s)\n"
                
                st.success(summary_msg)
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
        
        # Initialize selected files in session state
        if 'selected_files' not in st.session_state:
            st.session_state.selected_files = set()
        
        st.markdown(f"**Found {len(files)} file(s)**")
        
        # Selection controls
        if files:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write("")
            with col2:
                if st.button("✅ Select All", use_container_width=True):
                    for file_info in files:
                        file_id = file_info['id']
                        st.session_state.selected_files.add(file_id)
                        st.session_state[f"select_{file_id}"] = True
                    st.rerun()
            with col3:
                if st.button("❌ Deselect All", use_container_width=True):
                    st.session_state.selected_files = set()
                    for file_info in files:
                        file_id = file_info['id']
                        st.session_state[f"select_{file_id}"] = False
                    st.rerun()
        
        # Download selected files as zip
        if st.session_state.selected_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"📦 {len(st.session_state.selected_files)} file(s) selected for download")
            with col2:
                if st.button("📥 Download Selected as ZIP", type="primary", use_container_width=True):
                    selected_file_ids = list(st.session_state.selected_files)
                    zip_buffer = app.create_zip_from_files(selected_file_ids, db)
                    if zip_buffer:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        zip_filename = f"files_{timestamp}.zip"
                        st.download_button(
                            label="📥 Download ZIP File",
                            data=zip_buffer.getvalue(),
                            file_name=zip_filename,
                            mime="application/zip",
                            key="download_zip"
                        )
                        st.session_state.selected_files = set()
                        st.rerun()
        
        # Clear selection button
        if st.session_state.selected_files:
            if st.button("❌ Clear Selection", use_container_width=False):
                st.session_state.selected_files = set()
                st.rerun()
        
        st.markdown("---")
        
        # Display files with checkboxes
        if files:
            for file_info in files:
                file_id = file_info['id']
                checkbox_key = f"select_{file_id}"
                
                # Initialize checkbox state
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = file_id in st.session_state.selected_files
                
                with st.expander(f"{app.get_file_icon(file_info['file_type'])} {file_info['original_filename']}", expanded=False):
                    col1, col2, col3 = st.columns([0.5, 2.5, 1])
                    
                    with col1:
                        # Checkbox for selecting file
                        checkbox_value = st.checkbox("Select", value=st.session_state[checkbox_key], key=checkbox_key)
                        if checkbox_value:
                            st.session_state.selected_files.add(file_id)
                        else:
                            st.session_state.selected_files.discard(file_id)
                    
                    with col2:
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
                    
                    with col3:
                        file_path = Path(file_info['file_path'])
                        if file_path.exists():
                            # Download button (single file)
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                                db.update_file_access(file_info['id'])
                                st.download_button(
                                    label="📥 Download",
                                    data=file_data,
                                    file_name=file_info['original_filename'],
                                    key=f"download_{file_info['id']}"
                                )
                            
                            # Delete button - admin only
                            if is_admin:
                                if st.button("🗑️ Delete", key=f"delete_{file_info['id']}"):
                                    if db.delete_file(file_info['id']):
                                        st.session_state.selected_files.discard(file_info['id'])
                                        st.success("File deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete file")
                            else:
                                st.info("🔒 Only admins can delete files")
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
    
    # Files Type page
    elif page == "📁 Files Type":
        st.title("📁 Files by Type")
        st.markdown("View and manage files organized by file type")
        
        stats = db.get_stats()
        
        # Get files grouped by type
        all_files = db.get_files()
        
        # Group files by type
        files_by_type = {}
        for file_info in all_files:
            file_type = file_info.get('file_type', 'Unknown')
            # Categorize file type
            if file_type.startswith('image/'):
                type_group = 'Images'
            elif file_type.startswith('video/'):
                type_group = 'Videos'
            elif file_type.startswith('audio/'):
                type_group = 'Audio'
            elif file_type == 'application/pdf':
                type_group = 'PDFs'
            elif 'excel' in file_type or 'spreadsheet' in file_type:
                type_group = 'Spreadsheets'
            elif 'word' in file_type or 'document' in file_type:
                type_group = 'Documents'
            elif 'powerpoint' in file_type or 'presentation' in file_type:
                type_group = 'Presentations'
            elif file_type.startswith('text/'):
                type_group = 'Text Files'
            elif file_type.startswith('application/'):
                type_group = 'Applications'
            else:
                type_group = 'Other'
            
            if type_group not in files_by_type:
                files_by_type[type_group] = []
            files_by_type[type_group].append(file_info)
        
        # Display file counts by type
        st.subheader("📊 File Count by Type")
        
        if files_by_type:
            # Create summary cards
            type_counts = {k: len(v) for k, v in files_by_type.items()}
            sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Display metrics in columns
            num_cols = min(4, len(sorted_types))
            cols = st.columns(num_cols)
            
            for idx, (file_type, count) in enumerate(sorted_types):
                with cols[idx % num_cols]:
                    st.metric(file_type, count)
            
            st.markdown("---")
            
            # Display files grouped by type
            for file_type, files in sorted(files_by_type.items(), key=lambda x: len(x[1]), reverse=True):
                # Get icon for this file type
                icon = app.get_file_icon(files[0]['file_type']) if files else "📄"
                with st.expander(f"{icon} {file_type} ({len(files)} files)", expanded=False):
                    st.markdown(f"**Total: {len(files)} file(s)**")
                    
                    # Display files in this category
                    for file_info in files:
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.write(f"📄 **{file_info['original_filename']}**")
                            st.caption(f"Size: {app.format_file_size(file_info['file_size'])} | Category: {file_info['category']}")
                        
                        with col2:
                            st.caption(f"Uploaded: {file_info['uploaded_at']}")
                            st.caption(f"Accessed: {file_info['access_count']} times")
                        
                        with col3:
                            file_path = Path(file_info['file_path'])
                            if file_path.exists():
                                with open(file_path, "rb") as f:
                                    file_data = f.read()
                                    db.update_file_access(file_info['id'])
                                    st.download_button(
                                        label="📥",
                                        data=file_data,
                                        file_name=file_info['original_filename'],
                                        key=f"download_type_{file_info['id']}"
                                    )
                        
                        st.markdown("---")
        else:
            st.info("No files found. Upload some files to see them organized by type.")
    
    # Admin User Management page (admin only)
    elif page == "👑 User Management":
        if not is_admin:
            st.error("🔒 Access Denied: Admin privileges required to access User Management.")
            st.info("Please login as an administrator to access this page.")
            st.stop()
        
        # User Management page content
        st.title("👑 User Management")
        st.markdown("Manage user accounts and permissions")
        st.markdown("---")
        
        # Get all users
        all_users = db.get_all_users()
        
        if all_users:
            st.subheader("📋 All Users")
            
            # Display users in a table format
            for user in all_users:
                with st.expander(f"👤 {user['username']} {'👑' if user.get('is_admin', 0) else ''}"):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        st.write(f"**Username:** {user['username']}")
                        if user.get('email'):
                            st.write(f"**Email:** {user['email']}")
                        st.write(f"**Created:** {user.get('created_at', 'N/A')}")
                        st.write(f"**Last Login:** {user.get('last_login', 'Never')}")
                    
                    with col2:
                        admin_status = bool(user.get('is_admin', 0))
                        is_default_admin = user['username'] == 'Admin-Sujay'
                        
                        if is_default_admin:
                            st.info("👑 Default Admin Account")
                            st.caption("Cannot modify or delete")
                        else:
                            new_admin_status = st.checkbox(
                                "Admin Status",
                                value=admin_status,
                                key=f"admin_checkbox_{user['id']}"
                            )
                            if new_admin_status != admin_status:
                                if db.update_user_admin_status(user['id'], new_admin_status):
                                    st.success("Admin status updated!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update admin status")
                    
                    with col3:
                        if not is_default_admin:
                            if st.button(f"🗑️ Delete User", key=f"delete_user_{user['id']}"):
                                if db.delete_user(user['id']):
                                    st.success(f"User '{user['username']}' deleted!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete user")
                        else:
                            st.caption("Cannot delete default admin")
                    
                    st.markdown("---")
            
            # Summary
            total_users = len(all_users)
            admin_count = sum(1 for u in all_users if u.get('is_admin', 0))
            regular_users = total_users - admin_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", total_users)
            with col2:
                st.metric("Admin Users", admin_count)
            with col3:
                st.metric("Regular Users", regular_users)
        else:
            st.info("No users found.")


if __name__ == "__main__":
    main()

