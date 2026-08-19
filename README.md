# AI Video Factory

A scene-driven video production pipeline that transforms structured scripts into captioned vertical video deliverables.

## Overview

AI Video Factory is a local Python and FFmpeg prototype for assembling a vertical video from a structured JSON script. It resolves local visual assets, creates per-scene subtitle files, renders video clips with audio, validates those clips, and concatenates them into one final MP4.

The supported workflow is deliberately local and asset-driven. It does not generate scripts, images, or videos with an AI provider, and it does not publish to social platforms.

Media assets are not included in this repository. Add appropriately licensed visual and audio assets to the documented asset directories before running the example.

## Current status

**Working local prototype.** The supported core pipeline has been verified with `script_test.json` and produces a captioned vertical `final_video.mp4`.

## Architecture / pipeline

```text
Script JSON
  -> project loading and style selection
  -> cached/local visual asset resolution
  -> per-scene subtitle generation
  -> FFmpeg scene rendering
  -> scene validation
  -> FFmpeg final-video assembly
```

See [architecture documentation](docs/architecture.md) for the implementation flow.

## Features currently working

- Validates a JSON script containing a title, scenes, scene types, text, durations, and optional style.
- Resolves a scene asset from `05_visual_assets/` using a content-hash cache.
- Deterministically selects a local fallback asset when no cached asset exists.
- Selects the configured local style audio from `Audio_Assets/`.
- Creates one SRT subtitle file per scene.
- Renders captioned H.264/AAC scene clips with FFmpeg.
- Validates scene clip existence and duration with FFprobe.
- Concatenates validated scene clips into `final_video.mp4`.
- Stops with explicit errors when FFmpeg or FFprobe fails.

## Technology stack

- Python 3.10+ (standard library only for the supported core path)
- FFmpeg and FFprobe
- Local MP4 visual assets
- Local MP3 audio assets
- SRT subtitles rendered through FFmpeg/libass

## Project structure

```text
ai_video_factory.py        Supported command-line core pipeline
asset_system.py            Cached/local visual asset resolution
styles.json                Style definitions and configured music
script_test.json           Verified sample script
05_visual_assets/          Local visual-asset directory; only its README is published
Audio_Assets/              Local background-audio directory; not published
temp/                      Generated scene clips (ignored by Git)
subs/                      Generated scene subtitles (ignored by Git)
final_video.mp4            Generated final output (ignored by Git)
docs/architecture.md       Pipeline architecture documentation

# Kept for future stabilization; not part of the supported core workflow
app.py, studio.py, factory.py, publisher.py, topic_ai.py, style_ai.py,
money_ai.py, and related legacy/experimental files
```

## Prerequisites

- Python 3.10 or newer
- FFmpeg and FFprobe installed and available on your `PATH`
- Appropriately licensed local visual assets in `05_visual_assets/cinematic/` and `05_visual_assets/motion_graphics/`
- Appropriately licensed local audio assets in `Audio_Assets/`, including the filenames configured in `styles.json`

Check the media tools before running:

```bash
ffmpeg -version
ffprobe -version
```

## Installation

Clone or copy the project, then add appropriately licensed local assets to the documented asset directories. The verified core uses only Python's standard library, so `requirements.txt` intentionally has no pip packages to install.

Optionally create an isolated environment for future project work:

```bash
python -m venv .venv
```

## Running the verified example

From the project root, run:

```bash
python -B ai_video_factory.py script_test.json
```

`-B` prevents Python from writing bytecode cache files during the build. The command always rebuilds the scene clips and final output; it does not depend on `builds/*.done` markers.

### Sample input

[`script_test.json`](script_test.json) is the documented, verified sample input. Its JSON controls:

- `scenes`: the ordered sequence of video scenes.
- `scenes[].text`: the caption text and cache key used for the local visual asset.
- `scenes[].duration`: each scene's target duration in seconds.
- `style`: selects a configuration in `styles.json`, including its local audio file.

Each scene also declares a `type`: `CIN` selects from cinematic assets and `MG` selects from motion-graphics assets.

## Expected output

The command writes:

```text
temp/scene_0.mp4 ...  Rendered scene clips
subs/scene_0.srt ...   Generated per-scene captions
concat.txt             FFmpeg concat manifest
final_video.mp4        Final captioned vertical video
```

The verified sample produces a 1080x1920 H.264/AAC MP4 of approximately 13 seconds.

## Current limitations

- Visuals are selected from local assets; no AI image or video generation is part of the supported workflow.
- Audio is local background music, not generated narration.
- Subtitle rendering currently uses FFmpeg's default subtitle styling.
- The project is a local prototype and has not been hardened for production workloads, concurrent builds, or cloud deployment.
- Legacy UI, analytics, hooks, publishing, shorts, and format-conversion paths remain in the repository but are not part of the supported pipeline.

## Roadmap

- Continue stabilizing legacy and experimental paths independently from the supported core workflow.
- Improve configuration, test coverage, and repeatable verification.
- Document asset provenance and establish a deliberate release process.
- Evaluate future product capabilities only after the local pipeline remains stable.

## License and asset provenance

No license is currently declared for this repository. Before public distribution, confirm the license and redistribution rights for every visual asset, audio file, font, and generated deliverable. Keep a provenance record for externally sourced assets and do not publish material without the necessary rights.
