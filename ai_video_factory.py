DRY_RUN = False

print("AI Video Factory starting...")

from dataclasses import dataclass
from typing import List
import os
import subprocess
import json
import argparse
from asset_system import lookup_asset, generate_asset


STYLES = json.load(open("styles.json"))

@dataclass
class Scene:
    id: int
    scene_type: str      # "CIN" or "MG"
    text: str
    duration: float
    audio_path: str
    asset_path: str = ""
    temp_video: str = ""
    video: str = ""

@dataclass
class VideoProject:
    title: str
    scenes: List[Scene]
    style: dict
    fps: int = 30
    width: int = 1080
    height: int = 1920

def load_project(script_data):
    if not isinstance(script_data, dict):
        raise ValueError("Script JSON must contain an object")
    if not script_data.get("title"):
        raise ValueError("Script JSON requires a non-empty 'title'")
    if not isinstance(script_data.get("scenes"), list) or not script_data["scenes"]:
        raise ValueError("Script JSON requires at least one scene")

    style_name = script_data.get("style", "mindshift")
    if style_name not in STYLES:
        raise ValueError(f"Style '{style_name}' not found in styles.json")

    music_name = STYLES[style_name].get("music", "calm_ambient.mp3")
    audio_path = os.path.join("Audio_Assets", music_name)
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Style audio missing: {audio_path}")

    scenes = []

    for i, s in enumerate(script_data["scenes"]):
        if not isinstance(s, dict):
            raise ValueError(f"Scene {i} must be an object")
        scene_type = str(s.get("type", "")).upper()
        if scene_type not in {"CIN", "MG"}:
            raise ValueError(f"Scene {i} type must be 'CIN' or 'MG'")
        if not isinstance(s.get("text"), str) or not s["text"].strip():
            raise ValueError(f"Scene {i} requires non-empty text")
        try:
            duration = float(s["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Scene {i} requires a numeric duration") from exc
        if duration <= 0:
            raise ValueError(f"Scene {i} duration must be greater than zero")

        scene = Scene(
            id=i,
            scene_type=scene_type,
            text=s["text"],
            duration=duration,
            audio_path=audio_path
        )

        scene.temp_videos = {}

        scenes.append(scene)

    return VideoProject(
        title=script_data["title"],
        scenes=scenes,
        style=STYLES[style_name]
    )

def resolve_assets(project):
    for scene in project.scenes:
        asset = lookup_asset(scene.text, scene.scene_type)

        if asset:
            print(f"[FOUND][{scene.scene_type}] {asset}")
            scene.asset_path = asset
            continue

        print(f"[MISS][{scene.scene_type}] Generating new")

        generated = generate_asset(scene)

        # 🚨 HARD SAFETY CHECK
        if not generated:
            print(f"[WARN] Asset generation failed for scene {scene.id} ({scene.scene_type})")
            print("[FALLBACK] Forcing Motion Graphic")

            # Force fallback to MG
            scene.scene_type = "mg"
            generated = generate_asset(scene)

        if not generated:
            raise Exception(f"Asset generation failed for Scene {scene.id} even after fallback")

        scene.asset_path = generated


from factory_utils import get_last_scene, mark_scene_done

def render_scenes(project):
    print("\n==== RENDER SCENES ====")
    print("Total scenes:", len(project.scenes))

    os.makedirs("temp", exist_ok=True)

    for scene in project.scenes:
        print(f"\n[SCENE {scene.id}]")
        print("Type:", scene.scene_type)
        print("Asset:", scene.asset_path)
        print("Audio:", scene.audio_path)
        print("Duration:", scene.duration)

        output = f"temp/scene_{scene.id}.mp4"

        try:
            render_scene_ffmpeg(
                asset=scene.asset_path,
                audio=scene.audio_path,
                duration=scene.duration,
                subtitle=f"subs/scene_{scene.id}.srt",
                output=output,
                style=project.style
            )
        except Exception as e:
            print("render_scene_ffmpeg failed:", e)
            raise

        print("Exists after render:", os.path.exists(output))

        scene.temp_video = output
        scene.video = output


def assemble_final_video(project):
    concat_path = "concat.txt"
    output_path = "final_video.mp4"

    with open(concat_path, "w", encoding="utf-8") as f:
        for s in project.scenes:
            if not s.video:
                raise Exception(f"Scene {s.id} has no video")
            if not os.path.exists(s.video):
                raise Exception(f"Missing clip file: {s.video}")

            print(f"[CONCAT] {s.video}")
            f.write(f"file '{os.path.abspath(s.video)}'\n")

    print("\n==== concat.txt ====")
    print(open(concat_path, encoding="utf-8").read())

    result = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print("\n==== FFMPEG STDOUT ====")
    print(result.stdout)
    print("\n==== FFMPEG STDERR ====")
    print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed while concatenating scenes (exit {result.returncode})")
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("FFmpeg completed without creating a non-empty final_video.mp4")


import os
import subprocess

def get_duration(path):
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    return float(result.stdout.strip())


def guard_scene(scene):
    if not os.path.exists(scene.temp_video):
        raise Exception(f"Scene {scene.id} missing video")

    d = get_duration(scene.temp_video)

    if abs(d - scene.duration) > 0.1:
        raise Exception(f"Scene {scene.id} duration mismatch {d} vs {scene.duration}")

def build_video(script_data):
    project = load_project(script_data)
    resolve_assets(project)
    write_subtitles(project)
    render_scenes(project)

    validate_project(project)
    assemble_final_video(project)

    final_duration = get_duration("final_video.mp4")
    print(f"\n[COMPLETE] final_video.mp4 ({final_duration:.2f}s)")

    return project

def validate_project(project):
    print("\n==== VALIDATION ====")
    for s in project.scenes:
        print(f"[VALIDATE] Scene {s.id} video={s.video}")
        if not s.video:
            raise Exception(f"Scene {s.id} missing video")
        guard_scene(s)


def generate_scene_srt(scene):
    """
    Creates a basic single-line subtitle that spans the whole scene.
    """
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    start = "00:00:00,000"
    end = fmt(scene.duration)

    text = scene.text.replace("\n", " ")

    return f"1\n{start} --> {end}\n{text}\n"


def write_subtitles(project):
    os.makedirs("subs", exist_ok=True)

    for s in project.scenes:
        with open(f"subs/scene_{s.id}.srt", "w", encoding="utf-8") as f:
            f.write(generate_scene_srt(s))

def render_scene_ffmpeg(asset, audio, duration, subtitle, output, style):
    if not os.path.exists(asset):
        raise Exception(f"Asset missing: {asset}")

    if not os.path.exists(audio):
        raise Exception(f"Audio missing: {audio}")

    duration = max(1, float(duration))

    cmd = [
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
        output
    ]

    # Burn subtitles if present
    if subtitle and os.path.exists(subtitle):
        cmd.insert(-2, "-vf")
        # Keep the filter path relative. An absolute Windows drive path is
        # interpreted by FFmpeg's filter parser as an option separator.
        cmd.insert(-2, f"subtitles=filename='{subtitle.replace(os.sep, '/')}'")

    print("\n[FFMPEG]", " ".join(cmd))

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed while rendering {output} (exit {result.returncode})")
    if not os.path.exists(output) or os.path.getsize(output) == 0:
        raise RuntimeError(f"FFmpeg completed without creating a non-empty {output}")


def main():
    parser = argparse.ArgumentParser(description="Build a video from an AI Video Factory script JSON file.")
    parser.add_argument("script", help="Path to a script JSON file")
    args = parser.parse_args()

    with open(args.script, encoding="utf-8") as script_file:
        script_data = json.load(script_file)

    build_video(script_data)


if __name__ == "__main__":
    main()


def export_format(input_video, output, mode):
    if mode == "16x9":
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    elif mode == "1x1":
        vf = "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2"
    else:
        return

    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", vf,
        "-c:a", "copy",
        output
    ])


def generate_shorts(project):
    os.makedirs("shorts", exist_ok=True)

    for s in project.scenes:
        if s.duration >= 5 and s.duration <= 20:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", s.temp_video,
                f"shorts/short_{s.id}.mp4"
            ])


def make_loop(input, output):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input,
        "-filter_complex",
        "[0:v]tpad=stop_mode=clone:stop_duration=0.5[v]",
        "-map", "[v]",
        "-map", "0:a",
        output
    ])

def make_all_loops():
    if not os.path.exists("shorts"):
        return

    for f in os.listdir("shorts"):
        if f.endswith(".mp4") and not f.startswith("loop_"):
            make_loop(
                f"shorts/{f}",
                f"shorts/loop_{f}"
            )


def extract_hook(video):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video,
        "-t", "5",
        "shorts/hook.mp4"
    ])



def build_hooks(hooks):
    os.makedirs("hooks", exist_ok=True)

    for i, h in enumerate(hooks):
        generate_tts(h, f"hooks/h{i}.wav")
        render_scene_ffmpeg("hook_bg.mp4", f"hooks/h{i}.wav", 4, f"hooks/h{i}.mp4")

def export_format(input, output, ratio):
    print(f"[EXPORT] {output} ({ratio}) skipped — formatter not implemented yet")


def detect_drop(csv):
    import pandas as pd
    df = pd.read_csv(csv)
    drops = df[df["retention"] < 0.6]
    return drops["time"].min()


def auto_fix(project, drop_time):
    project.scenes = project.scenes[1:]
    project.scenes[0].duration = drop_time


