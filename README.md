# AI Video Factory

### Deterministic Video Production Pipeline

A Python and FFmpeg pipeline that transforms structured scene scripts into validated, captioned vertical video deliverables through deterministic asset resolution, automated rendering, and media-level verification.

> **Portfolio role:** This project is the deterministic production-engineering foundation for the AI/agent systems in my portfolio. It focuses on reliable, reproducible media-processing primitives rather than adding AI generation for its own sake.

> **Scope:** This repository contains the verified local rendering core. It does not currently use an AI provider to generate scripts, images, or video.

---

## 🎬 What It Does

The pipeline takes a small JSON scene script and produces a finished vertical MP4 through explicit validation gates:

```text
Structured Script
      ↓
Project Validation
      ↓
Asset Resolution + Cache
      ↓
Subtitle Generation
      ↓
FFmpeg Scene Rendering
      ↓
FFprobe Validation
      ↓
Final Video Assembly
```

### Core capabilities

- Validates structured JSON scene definitions before rendering.
- Resolves reusable local visual assets using deterministic content-based keys.
- Selects deterministic local fallback assets when a cache entry is unavailable.
- Generates per-scene SRT subtitles.
- Renders H.264/AAC scene clips with FFmpeg.
- Validates rendered scene duration with FFprobe before assembly.
- Concatenates validated scenes into a final MP4.
- Fails explicitly when required media or processing steps fail.

---

## 🧠 Engineering Highlights

### Deterministic asset resolution

Scene text and type are converted into a stable content hash. Existing cached assets are reused; otherwise a local fallback clip is selected deterministically and cached for subsequent builds. The same scene input therefore follows the same asset-resolution path.

### Validation gates

The pipeline does not treat successful process execution as sufficient. Structured input is validated before rendering, rendered scene files are checked for existence, and FFprobe verifies scene duration before final assembly.

### Reproducible local pipeline

The supported core uses Python's standard library and system FFmpeg/FFprobe executables, keeping the execution path small and easy to reproduce.

### Testable failure handling

The unit suite covers input validation, typed scene construction, subtitle generation, deterministic asset caching, missing renders, and FFprobe failure handling. GitHub Actions runs the unit suite on pushes and pull requests.

---

## 📁 Project Structure

```text
ai_video_factory.py         Core orchestration and CLI entry point
asset_system.py             Asset lookup, deterministic fallback, and cache
styles.json                 Local style configuration
script_test.json            Verified example input
05_visual_assets/           Local visual-asset directory; assets are not published
docs/architecture.md        Detailed pipeline architecture
tests/test_pipeline.py      Standard-library unit tests
.github/workflows/tests.yml CI workflow for the unit suite
requirements.txt            Documents the dependency-free Python core
```

Generated files are intentionally excluded from Git, including scene renders, subtitles, final videos, local media assets, and caches.

---

## ▶️ Run the Verified Example

### Prerequisites

- Python 3.10+
- FFmpeg installed and available on `PATH`
- FFprobe installed and available on `PATH`
- Appropriately licensed visual assets in:
  - `05_visual_assets/cinematic/`
  - `05_visual_assets/motion_graphics/`
- The local audio file configured by the selected style in `Audio_Assets/`

Check the media tools:

```bash
ffmpeg -version
ffprobe -version
```

### Build

From the project root:

```bash
python -B ai_video_factory.py script_test.json
```

The command creates:

```text
subs/scene_0.srt ...       Per-scene subtitles
temp/scene_0.mp4 ...       Rendered scene clips
concat.txt                 FFmpeg concat manifest
final_video.mp4            Final captioned vertical video
```

The verified example is a three-scene vertical video totaling approximately 13 seconds.

### Run tests

The test suite uses only Python's standard library:

```bash
python -m unittest discover -s tests -v
```

The same unit suite runs automatically in GitHub Actions for pushes and pull requests.

---

## 🏗️ Architecture

See [`docs/architecture.md`](docs/architecture.md) for the implementation flow, component responsibilities, asset-cache behavior, rendering process, validation checks, and final assembly stage.

---

## ⚠️ Current Scope & Limitations

This is a **working local video-production prototype**, not a production cloud service.

The current supported pipeline:

- uses local visual assets rather than AI-generated visuals;
- uses local background music rather than generated narration;
- uses simple scene-spanning subtitles;
- is designed for sequential local builds rather than concurrent workloads;
- does not publish directly to social platforms.

These constraints are intentional: the repository focuses on a small, verified media-rendering core rather than presenting unfinished experimental features as supported functionality.

---

## 🔭 Future Direction

Potential future work includes richer subtitle styling, broader media-format support, deeper integration tests around the FFmpeg/FFprobe boundary, asset provenance tracking, and additional production integrations.

Those capabilities are intentionally outside the current verified core until they can be implemented and tested as first-class pipeline stages.

---

## 📄 License & Asset Provenance

No software license is currently declared for this repository. Before redistribution, confirm the licensing terms for the code and the rights to every visual asset, audio file, font, and generated deliverable.
