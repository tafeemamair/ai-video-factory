"""Deterministic local asset lookup and fallback resolution."""

from __future__ import annotations

import hashlib
import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_video_factory import Scene


ASSET_DIR = "05_visual_assets"


def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def lookup_asset(text: str, scene_type: str) -> str | None:
    """Return a cached asset for a scene, if one exists."""
    key = f"{scene_type.upper()}_{_hash(text)}"
    path = os.path.join(ASSET_DIR, f"{key}.mp4")
    return path if os.path.exists(path) else None


def resolve_fallback_asset(scene: "Scene") -> str:
    """Select and cache a deterministic local fallback clip."""
    scene_type = scene.scene_type.upper()
    folder = os.path.join(
        ASSET_DIR,
        "cinematic" if scene_type == "CIN" else "motion_graphics",
    )

    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Asset directory missing: {folder}")

    files = sorted(
        filename for filename in os.listdir(folder)
        if filename.lower().endswith(".mp4")
    )
    if not files:
        raise FileNotFoundError(f"No MP4 assets found in {folder}")

    selected = files[int(_hash(scene.text), 16) % len(files)]
    source = os.path.join(folder, selected)
    output = os.path.join(
        ASSET_DIR,
        f"{scene_type}_{_hash(scene.text)}.mp4",
    )

    os.makedirs(ASSET_DIR, exist_ok=True)
    shutil.copy2(source, output)
    return output
