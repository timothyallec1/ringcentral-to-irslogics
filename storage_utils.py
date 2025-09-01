import os
import json
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# -------------------------------
# ENV HANDLING
# -------------------------------
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
    print("[🔑] Loaded secrets from .env.local")
else:
    print("[☁️] Using environment variables from Azure")

AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# -------------------------------
# BLOB SERVICE CLIENT
# -------------------------------
blob_service = None
if AZURE_CONN_STR:
    try:
        blob_service = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    except Exception as e:
        print(f"[⚠️] Failed to init Blob client: {e}")

# Deployment:
USE_BLOB = blob_service is not None and not os.path.exists(".env.local")

# Local dev:
# USE_BLOB = blob_service is not None

# -------------------------------
# HELPERS
# -------------------------------
def get_container_client(container_name: str):
    """Return a container client, create if missing."""
    if not USE_BLOB:
        return None
    container_client = blob_service.get_container_client(container_name)
    try:
        container_client.create_container()
    except Exception:
        pass
    return container_client

def upload_text_to_blob(content: str, container: str, blob_name: str):
    client = get_container_client(container)
    blob_client = client.get_blob_client(blob_name)
    blob_client.upload_blob(content, overwrite=True)
    return f"https://{blob_service.account_name}.blob.core.windows.net/{container}/{blob_name}"

def upload_file_to_blob(file_path: str, container: str, blob_name: str = None):
    client = get_container_client(container)
    if not blob_name:
        blob_name = os.path.basename(file_path)
    blob_client = client.get_blob_client(blob_name)
    with open(file_path, "rb") as f:
        blob_client.upload_blob(f, overwrite=True)
    return f"https://{blob_service.account_name}.blob.core.windows.net/{container}/{blob_name}"

def download_blob_to_text(container: str, blob_name: str) -> str:
    client = get_container_client(container)
    blob_client = client.get_blob_client(blob_name)
    return blob_client.download_blob().readall().decode()

def list_blobs(container: str, prefix: str = ""):
    client = get_container_client(container)
    return list(client.list_blobs(name_starts_with=prefix))

# -------------------------------
# JSON SAVE/LOAD SWITCH
# -------------------------------
def save_json(data, local_dir, filename, container):
    """
    Save JSON locally (if .env.local exists) or to blob (Azure).
    """
    if USE_BLOB:
        upload_text_to_blob(json.dumps(data, indent=2), container, filename)
        print(f"[💾] Saved to Blob: {container}/{filename}")
        return f"{container}/{filename}"
    else:
        os.makedirs(local_dir, exist_ok=True)
        path = os.path.join(local_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[💾] Saved locally: {path}")
        return path

def load_latest_json(local_dir, container):
    """
    Load most recent JSON from local (if .env.local exists) or from blob (Azure).
    """
    if USE_BLOB:
        blobs = list_blobs(container)
        if not blobs:
            raise FileNotFoundError(f"No blobs found in container {container}")
        latest = max(blobs, key=lambda b: b.last_modified)
        content = download_blob_to_text(container, latest.name)
        print(f"[📥] Loaded from Blob: {container}/{latest.name}")
        return json.loads(content)
    else:
        files = [os.path.join(local_dir, f) for f in os.listdir(local_dir) if f.endswith(".json")]
        if not files:
            raise FileNotFoundError(f"No files found in {local_dir}")
        latest = max(files, key=os.path.getctime)
        with open(latest, "r") as f:
            print(f"[📥] Loaded locally: {latest}")
            return json.load(f)
