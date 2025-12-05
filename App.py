import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
import os

st.set_page_config(page_title="Google Drive Business Folder Manager", layout="wide")

st.title("📁 Google Drive – Business Folder Manager")

# ----------------------------
# SIDEBAR — JSON Upload
# ----------------------------
st.sidebar.header("🔐 Google Service Account Login")

json_file = st.sidebar.file_uploader("Upload Google Service JSON", type=["json"])

if not json_file:
    st.info("Upload your Google Service Account JSON to begin.")
    st.stop()

# Create credentials
credentials = service_account.Credentials.from_service_account_info(
    json_file.read()
)

# Connect to Google Drive
drive_service = build("drive", "v3", credentials=credentials)

# ----------------------------
# Folder Structure
# ----------------------------
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

# ----------------------------
# Helper Functions
# ----------------------------

def find_folder_id(name, parent=None):
    """Return folder ID if exists, else None."""
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"
    if parent:
        query += f" and '{parent}' in parents"

    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])
    return items[0]["id"] if items else None


def create_folder(name, parent=None):
    """Create a folder if not exists; return folder ID."""
    existing_id = find_folder_id(name, parent)
    if existing_id:
        return existing_id

    folder_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent:
        folder_metadata["parents"] = [parent]

    folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
    return folder.get("id")


def list_files(folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType, webViewLink)",
    ).execute()
    return results.get("files", [])


# ----------------------------
# MAIN LOGIC
# ----------------------------

st.subheader("📦 Folder Creation & Status")

# Create main folder
main_folder_id = create_folder(MAIN_FOLDER_NAME)
st.success(f"Main Folder Ready: **{MAIN_FOLDER_NAME}**")

# Create all subfolders
folder_map = {}
for name in SUBFOLDERS:
    folder_map[name] = create_folder(name, main_folder_id)

# Show status table
st.write("### Folder Status")
status_rows = [{"Folder": k, "ID": v} for k, v in folder_map.items()]
st.table(status_rows)

# ----------------------------
# FILE UPLOAD SECTION
# ----------------------------
st.subheader("📤 Upload Files Into a Folder")

selected_folder = st.selectbox("Select Folder", SUBFOLDERS)
file_to_upload = st.file_uploader("Upload a File", type=None)

if file_to_upload:
    temp_path = os.path.join(tempfile.gettempdir(), file_to_upload.name)
    with open(temp_path, "wb") as f:
        f.write(file_to_upload.read())

    media = MediaFileUpload(temp_path, resumable=True)
    file_metadata = {
        "name": file_to_upload.name,
        "parents": [folder_map[selected_folder]],
    }

    drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    st.success(f"Uploaded **{file_to_upload.name}** to **{selected_folder}**.")


# ----------------------------
# VIEW FILES IN A FOLDER
# ----------------------------
st.subheader("📄 View Folder Contents")

view_folder = st.selectbox("Select Folder to View Files", SUBFOLDERS, key="view")

files = list_files(folder_map[view_folder])

if not files:
    st.warning("No files in this folder yet.")
else:
    for f in files:
        st.write(f"**{f['name']}** — [Open File]({f['webViewLink']})")
