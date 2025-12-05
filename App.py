import streamlit as st
import json
import tempfile
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

st.set_page_config(page_title="Google Drive Business Manager", layout="wide")

st.title("📁 Google Drive – Business Folder Manager")

# ---------------------------------------
# SIDEBAR — GOOGLE LOGIN
# ---------------------------------------
st.sidebar.header("🔐 Google Service Account Login")

json_file = st.sidebar.file_uploader("Upload Google Service JSON", type=["json"])

if not json_file:
    st.info("Upload your Google Service Account JSON to begin.")
    st.stop()

# Parse the JSON correctly
try:
    service_info = json.load(json_file)
except Exception:
    st.error("❌ Invalid JSON file. Please upload a valid Google Service Account key.")
    st.stop()

# Create Google Drive credentials
try:
    credentials = service_account.Credentials.from_service_account_info(service_info)
    drive_service = build("drive", "v3", credentials=credentials)
except Exception as e:
    st.error("❌ Could not authenticate with the provided JSON.\n\n" + str(e))
    st.stop()

st.success("✅ Google Service Account authenticated successfully!")

# ---------------------------------------
# FOLDER SETTINGS
# ---------------------------------------
MAIN_FOLDER_NAME = "Business Main Folder"

SUBFOLDERS = [
    "001 Administration",
    "002 Financial",
    "003 Marketing",
    "004 Operation",
    "005 Sale",
    "006 Legal",
    "007 To be file",
]


# ---------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------
def find_folder_id(name, parent=None):
    """Find folder ID by name."""
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"
    if parent:
        query += f" and '{parent}' in parents"

    results = drive_service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    items = results.get("files", [])
    return items[0]["id"] if items else None


def create_folder(name, parent=None):
    """Create folder if not exists."""
    existing_id = find_folder_id(name, parent)
    if existing_id:
        return existing_id

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder"
    }

    if parent:
        metadata["parents"] = [parent]

    folder = drive_service.files().create(
        body=metadata,
        fields="id"
    ).execute()

    return folder.get("id")


def list_files(folder_id):
    """List files inside a Drive folder."""
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType, webViewLink)"
    ).execute()

    return results.get("files", [])


# ---------------------------------------
# CREATE MAIN + SUBFOLDERS
# ---------------------------------------
st.subheader("📦 Folder Structure")

with st.spinner("Checking folders..."):

    # Create main folder
    main_folder_id = create_folder(MAIN_FOLDER_NAME)

    # Create subfolders
    folder_map = {}
    for folder in SUBFOLDERS:
        folder_map[folder] = create_folder(folder, main_folder_id)

st.success("📁 All folders ready!")

# Show folder table
st.write("### Folder Status")

st.table([
    {"Folder": name, "Folder ID": fid}
    for name, fid in folder_map.items()
])

# ---------------------------------------
# FILE UPLOADING
# ---------------------------------------
st.subheader("📤 Upload Files")

target_folder = st.selectbox("Select folder to upload into:", SUBFOLDERS)
uploaded_file = st.file_uploader("Choose a file to upload")

if uploaded_file:
    temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    media = MediaFileUpload(temp_path, resumable=True)

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [folder_map[target_folder]]
    }

    drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    st.success(f"✅ Uploaded **{uploaded_file.name}** to **{target_folder}**")

# ---------------------------------------
# FILE VIEWER
# ---------------------------------------
st.subheader("📄 View Folder Contents")

view_folder = st.selectbox("Select folder to view:", SUBFOLDERS, key="viewer")
files = list_files(folder_map[view_folder])

if not files:
    st.warning("No files in this folder yet.")
else:
    st.write("### Files:")
    for file in files:
        st.write(f"📄 **{file['name']}** — [Open]({file['webViewLink']})")
