import os
import hashlib
import subprocess

ASSET_DIR = "05_visual_assets"

os.makedirs(ASSET_DIR, exist_ok=True)

def _hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def lookup_asset(text, scene_type):
    key = f"{scene_type}_{_hash(text)}"
    path = f"{ASSET_DIR}/{key}.mp4"

    if os.path.exists(path):
        return path

    return None


import os
import shutil

def generate_asset(scene):
    os.makedirs(ASSET_DIR, exist_ok=True)
    
    scene_type = scene.scene_type.upper()

    if scene_type == "CIN":
        folder = "05_visual_assets/cinematic"
    else:
        folder = "05_visual_assets/motion_graphics"


    files = sorted(f for f in os.listdir(folder) if f.endswith(".mp4"))

    if not files:
        raise Exception(f"No clips found in {folder}")

    # Select deterministically so the same scene always resolves to the same
    # local fallback clip before it is cached.
    pick = files[int(_hash(scene.text), 16) % len(files)]
    src = os.path.join(folder, pick)

    key = f"{scene.scene_type}_{_hash(scene.text)}"
    out = f"{ASSET_DIR}/{key}.mp4"

    print(f"[ASSET] {scene.scene_type} → {pick}")

    # Copy instead of regenerate
    shutil.copy(src, out)

    return out
