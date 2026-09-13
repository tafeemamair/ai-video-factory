"""Build validated vertical videos from structured scene scripts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from asset_system import lookup_asset, resolve_fallback_asset


with open("styles.json", encoding="utf-8") as styles_file:
    STYLES: dict[str, dict[str, Any]] = json.load(styles_file)


@dataclass
class Scene:
    id: int
    scene_type: str
    text: str
    duration: float
    audio_path: str
    asset_path: str = ""
    video_path: str = ""


@dataclass
class VideoProject:
    title: str
    scenes: list[Scene]
    style: dict[str, Any]
    fps: int = 30
    width: int = 1080
    height: int = 1920


def load_project(script_data: dict[str, Any]) -> VideoProject:
    """Validate a structured script and convert it into a video project."""
    if not isinstance(script_data, dict):
        raise ValueError("Script JSON must contain an object")

    title = script_data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Script JSON requires a non-empty 'title'")

    scenes_data = script_data.get("scenes")
    if not isinstance(scenes_data, list) or not scenes_data:
        raise ValueError("Script JSON requires at least one scene")

    style_name = script_data.get("style", "mindshift")
    if style_name not in STYLES:
        raise ValueError(f"Style '{style_name}' not found in styles.json")

    music_name = STYLES[style_name].get("music", "calm_ambient.mp3")
    audio_path = os.path.join("Audio_Assets", music_name)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Style audio missing: {audio_path}")

    scenes: list[Scene] = []
    for index, scene_data in enumerate(scenes_data):
        if not isinstance(scene_data, dict):
            raise ValueError(f"Scene {index} must be an object")

        scene_type = str(scene_data.get("type", "")).upper()
        if scene_type not in {"CIN", "MG"}:
            raise ValueError(f"Scene {index} type must be 'CIN' or 'MG'")

        text = scene_data.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Scene {index} requires non-empty text")

        try:
            duration = float(scene_data["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Scene {index} requires a numeric duration") from exc

        if duration <= 0:
            raise ValueError(f"Scene {index} duration must be greater than zero")

        scenes.append(
            Scene(
                id=index,
                scene_type=scene_type,
                text=text,
                duration=duration,
                audio_path=audio_path,
            )
        )

    return VideoProject(title=title, scenes=scenes, style=STYLES[style_name])


def resolve_assets(project: VideoProject) -> None:
    """Resolve cached assets or deterministic local fallback assets."""
    for scene in project.scenes:
        cached_asset = lookup_asset(scene.text, scene.scene_type)
        if cached_asset:
            print(f"[CACHE HIT][{scene.scene_type}] {cached_asset}")
            scene.asset_path = cached_asset
            continue

        print(f"[CACHE MISS][{scene.scene_type}] Resolving fallback asset")
        scene.asset_path = resolve_fallback_asset(scene)
        print(f"[ASSET] {scene.asset_path}")


def generate_scene_srt(scene: Scene) -> str:
    """Create a single subtitle cue spanning the scene duration."""
    def format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        whole_seconds = int(seconds % 60)
        milliseconds = int(round((seconds - int(seconds)) * 1000))
        if milliseconds == 1000:
            whole_seconds += 1
            milliseconds = 0
        return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"

    text = scene.text.replace("\n", " ")
    return f"1\n00:00:00,000 --> {format_time(scene.duration)}\n{text}\n"


def write_subtitles(project: VideoProject) -> None:
    os.makedirs("subs", exist_ok=True)
    for scene in project.scenes:
        subtitle_path = f"subs/scene_{scene.id}.srt"
        with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
            subtitle_file.write(generate_scene_srt(scene))


def render_scene_ffmpeg(
    asset: str,
    audio: str,
    duration: float,
    subtitle: str,
    output: str,
) -> None:
    """Render one captioned scene and fail explicitly on FFmpeg errors."""
    if not os.path.exists(asset):
        raise FileNotFoundError(f"Asset missing: {asset}")
    if not os.path.exists(audio):
        raise FileNotFoundError(f"Audio missing: {audio}")

    duration = max(1.0, float(duration))
    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", asset,
        "-i", audio,
        "-t", str(duration),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
    ]

    if subtitle and os.path.exists(subtitle):
        subtitle_filter = f"subtitles=filename='{subtitle.replace(os.sep, '/')} '".rstrip()
        command.extend(["-vf", subtitle_filter])

    command.append(output)
    print("[FFMPEG]", " ".join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed while rendering {output} (exit {result.returncode})\n"
            f"{result.stderr.strip()}"
        )
    if not os.path.exists(output) or os.path.getsize(output) == 0:
        raise RuntimeError(f"FFmpeg created no valid output at {output}")


def render_scenes(project: VideoProject) -> None:
    os.makedirs("temp", exist_ok=True)

    for scene in project.scenes:
        output = f"temp/scene_{scene.id}.mp4"
        render_scene_ffmpeg(
            asset=scene.asset_path,
            audio=scene.audio_path,
            duration=scene.duration,
            subtitle=f"subs/scene_{scene.id}.srt",
            output=output,
        )
        scene.video_path = output


def get_duration(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed for {path}: {result.stderr.strip()}")
    return float(result.stdout.strip())


def validate_project(project: VideoProject) -> None:
    """Verify every rendered scene before final assembly."""
    for scene in project.scenes:
        if not scene.video_path or not os.path.exists(scene.video_path):
            raise RuntimeError(f"Scene {scene.id} has no rendered video")

        actual_duration = get_duration(scene.video_path)
        if abs(actual_duration - scene.duration) > 0.1:
            raise RuntimeError(
                f"Scene {scene.id} duration mismatch: "
                f"{actual_duration:.3f}s vs {scene.duration:.3f}s"
            )


def assemble_final_video(project: VideoProject) -> str:
    """Concatenate validated scenes into the final vertical MP4."""
    concat_path = "concat.txt"
    output_path = "final_video.mp4"

    with open(concat_path, "w", encoding="utf-8") as concat_file:
        for scene in project.scenes:
            if not scene.video_path or not os.path.exists(scene.video_path):
                raise RuntimeError(f"Missing validated scene {scene.id}")
            concat_file.write(f"file '{os.path.abspath(scene.video_path)}'\n")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            output_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed while assembling the final video "
            f"(exit {result.returncode})\n{result.stderr.strip()}"
        )
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Final video was not created successfully")

    return output_path


def build_video(script_data: dict[str, Any]) -> VideoProject:
    """Run the complete build-and-validate pipeline."""
    project = load_project(script_data)
    resolve_assets(project)
    write_subtitles(project)
    render_scenes(project)
    validate_project(project)
    output = assemble_final_video(project)
    print(f"[COMPLETE] {output} ({get_duration(output):.2f}s)")
    return project


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a validated vertical video from a scene JSON script."
    )
    parser.add_argument("script", help="Path to the input JSON script")
    args = parser.parse_args()

    with open(args.script, encoding="utf-8") as script_file:
        script_data = json.load(script_file)

    build_video(script_data)


if __name__ == "__main__":
    main()
