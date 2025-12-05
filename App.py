import streamlit as st
import json
import tempfile
import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pandas as pd

st.set_page_config(page_title="Google Drive Business Manager Pro", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------
# CUSTOM CSS STYLING
# ---------------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    .folder-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin: 15px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .folder-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .stat-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .canvas-folder {
        background: #f8f9fa;
        border: 2px dashed #667eea;
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        position: relative;
    }
    .canvas-subfolder {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 20px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .canvas-subfolder:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }
    .file-item {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 6px;
        margin: 8px 0;
        border-left: 3px solid #28a745;
    }
    .breadcrumb {
        background: #e9ecef;
        padding: 10px 15px;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------
# APP NAVIGATION
# ---------------------------------------
st.sidebar.markdown("### 🧭 Navigation Center")
page = st.sidebar.radio(
    "Select Module:",
    [
        "🏠 Dashboard",
        "📁 Folder Manager",
        "📤 Upload Center",
        "📄 File Browser",
        "🔍 Search Files",
        "🧩 Canvas View",
        "📊 Analytics",
        "⚙️ Settings",
        "🗑️ Trash Manager"
    ]
)

# ---------------------------------------
# SIDEBAR — GOOGLE LOGIN
# ---------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔐 Authentication")

json_file = st.sidebar.file_uploader("Service Account JSON", type=["json"], help="Upload your Google Service Account credentials")

if not json_file:
    st.markdown("""
    <div class="main-header">
        <h1>📁 Google Drive Business Manager Pro</h1>
        <p>Enterprise-Grade Cloud Storage Management</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("🔑 Please upload your Google Service Account JSON file to begin.")
    
    st.info("""
    **How to get started:**
    1. Create a Google Cloud Project
    2. Enable Google Drive API
    3. Create a Service Account
    4. Download the JSON key file
    5. Upload it using the sidebar
    """)
    st.stop()

# Parse JSON
try:
    service_info = json.load(json_file)
    st.sidebar.success("✅ Credentials loaded")
except Exception as e:
    st.sidebar.error("❌ Invalid JSON file")
    st.stop()

# Authenticate
try:
    credentials = service_account.Credentials.from_service_account_info(
        service_info,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build("drive", "v3", credentials=credentials)
    st.sidebar.success("✅ Connected to Google Drive")
except Exception as e:
    st.sidebar.error(f"❌ Authentication failed: {str(e)}")
    st.stop()

# ---------------------------------------
# FOLDER CONFIGURATION
# ---------------------------------------
MAIN_FOLDER_NAME = "Business Main Folder"

SUBFOLDERS = {
    "001 Administration": {
        "icon": "🏢",
        "description": "Documents, policies, HR files, internal records, company handbook",
        "color": "#667eea"
    },
    "002 Financial": {
        "icon": "💰",
        "description": "Invoices, receipts, taxes, payroll, banking, financial statements",
        "color": "#f5576c"
    },
    "003 Marketing": {
        "icon": "📢",
        "description": "Ads, branding, media assets, campaigns, social media content",
        "color": "#f093fb"
    },
    "004 Operation": {
        "icon": "⚙️",
        "description": "Systems, SOPs, procedures, workflows, operational guidelines",
        "color": "#4facfe"
    },
    "005 Sale": {
        "icon": "💼",
        "description": "Sales scripts, leads, customer files, proposals, contracts",
        "color": "#43e97b"
    },
    "006 Legal": {
        "icon": "⚖️",
        "description": "Contracts, licenses, agreements, legal documents, compliance",
        "color": "#fa709a"
    },
    "007 To be file": {
        "icon": "📋",
        "description": "Unsorted files to be organized later, temporary storage",
        "color": "#feca57"
    }
}

# ---------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------
def find_folder_id(name, parent=None):
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent:
        query += f" and '{parent}' in parents"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])
    return items[0]["id"] if items else None

def create_folder(name, parent=None):
    existing_id = find_folder_id(name, parent)
    if existing_id:
        return existing_id
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent:
        metadata["parents"] = [parent]
    folder = drive_service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")

def list_files(folder_id, include_folders=True):
    query = f"'{folder_id}' in parents and trashed = false"
    if not include_folders:
        query += " and mimeType != 'application/vnd.google-apps.folder'"
    
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, iconLink)",
        orderBy="name"
    ).execute()
    return results.get("files", [])

def get_folder_stats(folder_id):
    files = list_files(folder_id, include_folders=False)
    total_size = sum(int(f.get('size', 0)) for f in files if f.get('size'))
    return {
        "file_count": len(files),
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }

def delete_file(file_id):
    drive_service.files().delete(fileId=file_id).execute()

def search_files(query_text):
    query = f"name contains '{query_text}' and trashed = false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, mimeType, webViewLink, parents)",
        pageSize=50
    ).execute()
    return results.get("files", [])

def get_file_icon(mime_type):
    icons = {
        "application/pdf": "📄",
        "application/vnd.google-apps.document": "📝",
        "application/vnd.google-apps.spreadsheet": "📊",
        "application/vnd.google-apps.presentation": "📽️",
        "application/vnd.google-apps.folder": "📁",
        "image/": "🖼️",
        "video/": "🎥",
        "audio/": "🎵"
    }
    for key, icon in icons.items():
        if mime_type.startswith(key):
            return icon
    return "📎"

# Initialize folder system
main_folder_id = create_folder(MAIN_FOLDER_NAME)
folder_map = {name: create_folder(name, main_folder_id) for name in SUBFOLDERS.keys()}

# ---------------------------------------
# SESSION STATE
# ---------------------------------------
if 'current_folder' not in st.session_state:
    st.session_state.current_folder = None

# ===================================================================
# 🏠 DASHBOARD PAGE
# ===================================================================
if page == "🏠 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>📁 Google Drive Business Manager Pro</h1>
        <p>Enterprise-Grade Cloud Storage Management System</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick Stats
    st.subheader("📊 Quick Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_files = 0
    total_size = 0
    
    for folder_id in folder_map.values():
        stats = get_folder_stats(folder_id)
        total_files += stats['file_count']
        total_size += stats['total_size']
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #667eea;">📁</h3>
            <h2>{len(SUBFOLDERS)}</h2>
            <p>Total Folders</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #f5576c;">📄</h3>
            <h2>{total_files}</h2>
            <p>Total Files</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #43e97b;">💾</h3>
            <h2>{round(total_size / (1024 * 1024), 1)} MB</h2>
            <p>Storage Used</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #f093fb;">✅</h3>
            <h2>Active</h2>
            <p>System Status</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Folder Overview
    st.subheader("📂 Folder Overview")
    
    for folder_name, folder_info in SUBFOLDERS.items():
        folder_id = folder_map[folder_name]
        stats = get_folder_stats(folder_id)
        
        with st.expander(f"{folder_info['icon']} {folder_name} - {stats['file_count']} files ({stats['total_size_mb']} MB)"):
            st.write(f"**Description:** {folder_info['description']}")
            st.write(f"**Files:** {stats['file_count']}")
            st.write(f"**Size:** {stats['total_size_mb']} MB")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"View Files", key=f"view_{folder_name}"):
                    st.session_state.current_folder = folder_name
                    st.rerun()
            with col2:
                st.link_button("Open in Drive", f"https://drive.google.com/drive/folders/{folder_id}")

    st.markdown("---")
    
    st.info("""
    **💡 Quick Tips:**
    - Use the **Canvas View** for a visual representation of your folder structure
    - **Search Files** to find documents across all folders
    - Check **Analytics** for detailed insights into your storage usage
    - Use **Upload Center** for batch file uploads
    """)

# ===================================================================
# 📁 FOLDER MANAGER PAGE
# ===================================================================
elif page == "📁 Folder Manager":
    st.title("📁 Advanced Folder Manager")
    st.write("Comprehensive management of your business folder structure.")

    tab1, tab2, tab3 = st.tabs(["📋 Folder List", "🔗 Folder Links", "📊 Folder Details"])
    
    with tab1:
        st.subheader("Business Folder Structure")
        
        for folder_name, folder_info in SUBFOLDERS.items():
            folder_id = folder_map[folder_name]
            stats = get_folder_stats(folder_id)
            
            st.markdown(f"""
            <div class="folder-card">
                <h3>{folder_info['icon']} {folder_name}</h3>
                <p><strong>Description:</strong> {folder_info['description']}</p>
                <p><strong>Files:</strong> {stats['file_count']} | <strong>Size:</strong> {stats['total_size_mb']} MB</p>
                <p><strong>Folder ID:</strong> <code>{folder_id}</code></p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        st.subheader("Quick Access Links")
        st.write("Click to open folders directly in Google Drive:")
        
        for folder_name, folder_id in folder_map.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{SUBFOLDERS[folder_name]['icon']} **{folder_name}**")
            with col2:
                st.link_button("Open", f"https://drive.google.com/drive/folders/{folder_id}", key=f"link_{folder_name}")
    
    with tab3:
        st.subheader("Detailed Folder Information")
        
        data = []
        for folder_name, folder_id in folder_map.items():
            stats = get_folder_stats(folder_id)
            data.append({
                "Folder": folder_name,
                "Icon": SUBFOLDERS[folder_name]['icon'],
                "Files": stats['file_count'],
                "Size (MB)": stats['total_size_mb'],
                "Folder ID": folder_id
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

# ===================================================================
# 📤 UPLOAD CENTER PAGE
# ===================================================================
elif page == "📤 Upload Center":
    st.title("📤 Advanced Upload Center")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Files to Google Drive")
        
        target_folder = st.selectbox(
            "Select destination folder:",
            list(SUBFOLDERS.keys()),
            format_func=lambda x: f"{SUBFOLDERS[x]['icon']} {x}"
        )
        
        st.info(f"📝 {SUBFOLDERS[target_folder]['description']}")
        
        uploaded_files = st.file_uploader(
            "Choose files to upload (multiple files supported)",
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} file(s) ready to upload**")
            
            if st.button("🚀 Upload All Files", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {uploaded_file.name}...")
                    
                    temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.read())
                    
                    media = MediaFileUpload(temp_path, resumable=True)
                    metadata = {
                        "name": uploaded_file.name,
                        "parents": [folder_map[target_folder]]
                    }
                    
                    drive_service.files().create(
                        body=metadata,
                        media_body=media,
                        fields="id"
                    ).execute()
                    
                    os.remove(temp_path)
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                status_text.empty()
                progress_bar.empty()
                st.success(f"✅ Successfully uploaded {len(uploaded_files)} file(s) to **{target_folder}**")
    
    with col2:
        st.subheader("📊 Upload Statistics")
        
        if uploaded_files:
            total_size = sum(f.size for f in uploaded_files)
            st.metric("Files Selected", len(uploaded_files))
            st.metric("Total Size", f"{round(total_size / (1024 * 1024), 2)} MB")
            
            st.write("**File List:**")
            for f in uploaded_files:
                st.write(f"• {f.name} ({round(f.size / 1024, 1)} KB)")

# ===================================================================
# 📄 FILE BROWSER PAGE
# ===================================================================
elif page == "📄 File Browser":
    st.title("📄 Advanced File Browser")
    
    selected_folder = st.selectbox(
        "Select folder to browse:",
        list(SUBFOLDERS.keys()),
        format_func=lambda x: f"{SUBFOLDERS[x]['icon']} {x}"
    )
    
    st.markdown(f"""
    <div class="breadcrumb">
        📁 Business Main Folder / {SUBFOLDERS[selected_folder]['icon']} {selected_folder}
    </div>
    """, unsafe_allow_html=True)
    
    files = list_files(folder_map[selected_folder], include_folders=False)
    
    if not files:
        st.warning("📭 This folder is empty. Upload files using the Upload Center.")
    else:
        st.write(f"**Found {len(files)} file(s)**")
        
        # View options
        view_mode = st.radio("View Mode:", ["Detailed List", "Grid View"], horizontal=True)
        
        if view_mode == "Detailed List":
            for file in files:
                icon = get_file_icon(file['mimeType'])
                size = round(int(file.get('size', 0)) / 1024, 1) if file.get('size') else 'N/A'
                modified = file.get('modifiedTime', 'Unknown')[:10]
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"{icon} **{file['name']}**")
                with col2:
                    st.write(f"{size} KB")
                with col3:
                    st.write(modified)
                with col4:
                    if st.button("🗑️", key=f"del_{file['id']}", help="Delete file"):
                        delete_file(file['id'])
                        st.rerun()
                
                st.markdown(f"[Open in Drive]({file['webViewLink']})")
                st.markdown("---")
        
        else:  # Grid View
            cols = st.columns(3)
            for idx, file in enumerate(files):
                with cols[idx % 3]:
                    icon = get_file_icon(file['mimeType'])
                    st.markdown(f"""
                    <div class="file-item" style="text-align: center;">
                        <h2>{icon}</h2>
                        <p><strong>{file['name'][:20]}...</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("Open", file['webViewLink'], key=f"open_{file['id']}")

# ===================================================================
# 🔍 SEARCH FILES PAGE
# ===================================================================
elif page == "🔍 Search Files":
    st.title("🔍 Advanced File Search")
    
    st.write("Search across all folders in your business drive:")
    
    search_query = st.text_input("Enter search term:", placeholder="e.g., invoice, contract, report")
    
    if search_query:
        with st.spinner("Searching..."):
            results = search_files(search_query)
        
        if not results:
            st.warning(f"No files found matching '{search_query}'")
        else:
            st.success(f"Found {len(results)} file(s) matching '{search_query}'")
            
            for file in results:
                icon = get_file_icon(file['mimeType'])
                
                # Find which folder it belongs to
                parent_folder = "Unknown"
                if file.get('parents'):
                    for fname, fid in folder_map.items():
                        if fid in file['parents']:
                            parent_folder = fname
                            break
                
                st.markdown(f"""
                <div class="file-item">
                    <h4>{icon} {file['name']}</h4>
                    <p>📁 Location: {parent_folder}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.link_button("Open File", file['webViewLink'], key=f"search_{file['id']}")
                st.markdown("---")

# ===================================================================
# 🧩 CANVAS VIEW PAGE
# ===================================================================
elif page == "🧩 Canvas View":
    st.title("🧩 Interactive Canvas View")
    
    st.write("Visual representation of your complete folder structure:")
    
    # Main folder canvas
    st.markdown(f"""
    <div class="canvas-folder">
        <h2 style="text-align: center; color: #667eea;">📁 {MAIN_FOLDER_NAME}</h2>
        <p style="text-align: center; color: #666;">Root Business Folder</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Subfolders in canvas style
    for folder_name, folder_info in SUBFOLDERS.items():
        folder_id = folder_map[folder_name]
        stats = get_folder_stats(folder_id)
        
        st.markdown(f"""
        <div class="canvas-subfolder">
            <h3>{folder_info['icon']} {folder_name}</h3>
            <p style="color: #666; font-size: 14px;">{folder_info['description']}</p>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <span>📄 {stats['file_count']} files</span>
                <span>💾 {stats['total_size_mb']} MB</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"View Files", key=f"canvas_view_{folder_name}"):
                st.session_state.current_folder = folder_name
        with col2:
            st.link_button("Open in Drive", f"https://drive.google.com/drive/folders/{folder_id}", key=f"canvas_open_{folder_name}")
        with col3:
            if st.button(f"Quick Upload", key=f"canvas_upload_{folder_name}"):
                st.info(f"Navigate to Upload Center and select {folder_name}")
        
        st.markdown("<br>", unsafe_allow_html=True)

# ===================================================================
# 📊 ANALYTICS PAGE
# ===================================================================
elif page == "📊 Analytics":
    st.title("📊 Storage Analytics Dashboard")
    
    st.subheader("Folder Size Distribution")
    
    folder_data = []
    for folder_name, folder_id in folder_map.items():
        stats = get_folder_stats(folder_id)
        folder_data.append({
            "Folder": folder_name,
            "Files": stats['file_count'],
            "Size (MB)": stats['total_size_mb']
        })
    
    df = pd.DataFrame(folder_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.bar_chart(df.set_index("Folder")["Files"])
        st.caption("File Count by Folder")
    
    with col2:
        st.bar_chart(df.set_index("Folder")["Size (MB)"])
        st.caption("Storage Usage by Folder (MB)")
    
    st.markdown("---")
    
    st.subheader("Detailed Statistics")
    st.dataframe(df, use_container_width=True)
    
    total_files = df["Files"].sum()
    total_size = df["Size (MB)"].sum()
    avg_size = round(total_size / len(df), 2)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Files", total_files)
    col2.metric("Total Storage", f"{total_size} MB")
    col3.metric("Average per Folder", f"{avg_size} MB")

# ===================================================================
# ⚙️ SETTINGS PAGE
# ===================================================================
elif page == "⚙️ Settings":
    st.title("⚙️ System Settings")
    
    st.subheader("Folder Configuration")
    st.write("Current folder structure:")
    st.json({name: info['description'] for name, info in SUBFOLDERS.items()})
    
    st.markdown("---")
    
    st.subheader("Drive Information")
    st.write(f"**Main Folder ID:** `{main_folder_id}`")
    st.write(f"**Service Account:** {service_info.get('client_email', 'Unknown')}")
    st.write(f"**Total Subfolders:** {len(SUBFOLDERS)}")
    
    st.markdown("---")
    
    st.subheader("System Actions")
    
    if st.button("🔄 Refresh Folder Structure"):
        st.rerun()
    
    st.warning("⚠️ Danger Zone")
    if st.checkbox("Show advanced options"):
        st.error("These actions cannot be undone!")
        if st.button("Clear all files (keep folders)"):
            st.warning("This feature is disabled for safety")

# ===================================================================
# 🗑️ TRASH MANAGER PAGE
# ===================================================================
elif page == "🗑️ Trash Manager":
    st.title("🗑️ Trash Manager")
    
    st.info("View and manage recently deleted files")
    
    try:
        results = drive_service.files().list(
            q="trashed = true",
            fields="files(id, name, trashedTime, mimeType)",
            pageSize=50
        ).execute()
        
        trashed_files = results.get("files", [])
        
        if not trashed_files:
            st.success("✅ Trash is empty!")
        else:
            st.warning(f"Found {len(trashed_files)} file(s) in trash")
            
            for file in trashed_files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    icon = get_file_icon(file['mimeType'])
                    st.write(f"{icon} **{file['name']}**")
                    st.caption(f"Deleted: {file.get('trashedTime', 'Unknown')[:10]}")
                with col2:
                    if st.button("Restore", key=f"restore_{file['id']}"):
                        drive_service.files().update(
                            fileId=file['id'],
                            body={'trashed': False}
                        ).execute()
                        st.success(f"Restored {file['name']}")
                        st.rerun()
                
                st.markdown("---")
    
    except Exception as e:
        st.error(f"Error accessing trash: {str(e)}")
