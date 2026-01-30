"""
Script to auto-download models from Hugging Face if missing
"""
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
import pipeline.config as config

def download_if_missing(repo_id, local_dir):
    local_dir = Path(local_dir)
    if not local_dir.exists() or not any(local_dir.iterdir()):
        print(f"Downloading {repo_id} to {local_dir}...")
        try:
            snapshot_download(repo_id=repo_id, local_dir=local_dir)
            print("Download complete.")
        except Exception as e:
            print(f"Failed to download {repo_id}: {e}")
            print("Please check your internet connection and try again.")
            sys.exit(1)
    else:
        print(f"Model {repo_id} already exists at {local_dir}")

def main():
    print("Checking models...")
    
    # Text Only Model
    download_if_missing("lightonai/LightOnOCR-2-1B", config.MODEL_PATHS["text_only"])
    
    # Text + BBox Model
    download_if_missing("lightonai/LightOnOCR-2-1B-bbox", config.MODEL_PATHS["text_img"])

if __name__ == "__main__":
    main()
