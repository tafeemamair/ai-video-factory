# Architecture

## Supported pipeline

```text
Script JSON
  -> project loading
  -> asset resolution/cache
  -> subtitle generation
  -> scene rendering
  -> validation
  -> final video assembly
```

The supported entry point is:

```bash
python -B ai_video_factory.py script_test.json
```

It operates only on the local, verified rendering pipeline. It does not invoke the UI, analytics, hooks, publishing, shorts, format-conversion, or legacy application flows.

## Pipeline stages

### 1. Script JSON

The input provides a title, an optional style name, and an ordered `scenes` array. Each scene supplies a `type` (`CIN` or `MG`), caption text, and a positive duration in seconds.

### 2. Project loading

`ai_video_factory.py` loads `styles.json`, validates the input, builds `Scene` objects, and chooses the style's audio file from `Audio_Assets/`.

### 3. Asset resolution and cache

`asset_system.py` derives a stable content hash from scene text and scene type. If a matching MP4 is already present directly under `05_visual_assets/`, it is reused as the cache entry.

When no cache entry exists, the module selects a deterministic local fallback from one of these folders:

- `05_visual_assets/cinematic/` for `CIN` scenes
- `05_visual_assets/motion_graphics/` for `MG` scenes

The selected clip is copied to the content-addressed cache path. This is local asset resolution, not visual generation.

### 4. Subtitle generation

`ai_video_factory.py` creates `subs/scene_<id>.srt` for every scene. Each subtitle spans that scene's target duration and contains the scene text.

### 5. Scene rendering

`render_scene_ffmpeg()` calls FFmpeg once per scene. It loops the local visual clip as needed, pairs it with the configured local audio, burns in the scene SRT subtitle, and writes a H.264/AAC clip to `temp/scene_<id>.mp4`.

FFmpeg failures are explicit: a nonzero exit code, absent output, or empty output raises an error and stops the pipeline.

### 6. Validation

`validate_project()` checks that every rendered scene clip exists. `guard_scene()` invokes FFprobe and confirms that each clip duration matches the scene duration within a small tolerance.

### 7. Final video assembly

`assemble_final_video()` writes `concat.txt` from the validated scene clip paths and asks FFmpeg to concatenate and encode them into `final_video.mp4`. The final file must exist and be non-empty; otherwise the build fails.

## Component roles

| Component | Role |
| --- | --- |
| `ai_video_factory.py` | Core orchestration, validation, subtitle creation, FFmpeg calls, and CLI entry point. |
| `asset_system.py` | Content-addressed lookup and deterministic selection of local visual assets. |
| FFmpeg | Renders individual captioned clips and assembles the final MP4. |
| FFprobe | Checks rendered scene durations. |
| `05_visual_assets/` | Local source clips and the direct asset-cache location. |
| `Audio_Assets/` | Local audio selected by a style definition. |
| `subs/` | Generated SRT files used by the FFmpeg subtitle filter. |
| `temp/` | Generated scene clips used for final assembly. |
