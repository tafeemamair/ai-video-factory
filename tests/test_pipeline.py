import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_video_factory as factory
import asset_system


class PipelineValidationTests(unittest.TestCase):
    def test_load_project_rejects_missing_title(self):
        with self.assertRaisesRegex(ValueError, "non-empty 'title'"):
            factory.load_project({"scenes": [{"type": "CIN", "text": "Intro", "duration": 2}]})

    def test_load_project_rejects_invalid_scene_type(self):
        data = {
            "title": "Test",
            "scenes": [{"type": "UNKNOWN", "text": "Intro", "duration": 2}],
        }
        with patch.dict(factory.STYLES, {"mindshift": {"music": "calm_ambient.mp3"}}, clear=True), patch(
            "ai_video_factory.os.path.exists", return_value=True
        ):
            with self.assertRaisesRegex(ValueError, "must be 'CIN' or 'MG'"):
                factory.load_project(data)

    def test_load_project_rejects_non_positive_duration(self):
        data = {
            "title": "Test",
            "scenes": [{"type": "CIN", "text": "Intro", "duration": 0}],
        }
        with patch.dict(factory.STYLES, {"mindshift": {"music": "calm_ambient.mp3"}}, clear=True), patch(
            "ai_video_factory.os.path.exists", return_value=True
        ):
            with self.assertRaisesRegex(ValueError, "duration must be greater than zero"):
                factory.load_project(data)

    def test_load_project_builds_typed_scenes(self):
        data = {
            "title": "Test",
            "style": "mindshift",
            "scenes": [
                {"type": "cin", "text": "Opening", "duration": 2.5},
                {"type": "MG", "text": "Closing", "duration": 1},
            ],
        }
        style = {"music": "calm_ambient.mp3"}
        with patch.dict(factory.STYLES, {"mindshift": style}, clear=True), patch(
            "ai_video_factory.os.path.exists", return_value=True
        ):
            project = factory.load_project(data)

        self.assertEqual(project.title, "Test")
        self.assertEqual([scene.scene_type for scene in project.scenes], ["CIN", "MG"])
        self.assertEqual([scene.duration for scene in project.scenes], [2.5, 1.0])


class SubtitleTests(unittest.TestCase):
    def test_generate_scene_srt_uses_scene_duration(self):
        scene = factory.Scene(
            id=0,
            scene_type="CIN",
            text="Hello\nworld",
            duration=2.5,
            audio_path="music.mp3",
        )
        srt = factory.generate_scene_srt(scene)
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt)
        self.assertIn("Hello world", srt)


class AssetResolutionTests(unittest.TestCase):
    def test_fallback_asset_selection_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cinematic = root / "cinematic"
            cinematic.mkdir()
            for filename in ("b.mp4", "a.mp4", "c.mp4"):
                (cinematic / filename).write_bytes(b"test")

            with patch.object(asset_system, "ASSET_DIR", temp_dir):
                scene = factory.Scene(0, "CIN", "same scene", 2, "music.mp3")
                first = asset_system.resolve_fallback_asset(scene)

                cached = asset_system.lookup_asset("same scene", "CIN")
                self.assertEqual(first, cached)
                self.assertTrue(os.path.exists(first))

                second = asset_system.resolve_fallback_asset(scene)
                self.assertEqual(first, second)

    def test_lookup_asset_misses_when_cache_entry_is_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            asset_system, "ASSET_DIR", temp_dir
        ):
            self.assertIsNone(asset_system.lookup_asset("missing", "CIN"))


class MediaValidationTests(unittest.TestCase):
    def test_validate_project_rejects_missing_render(self):
        project = factory.VideoProject(title="Test", scenes=[] , style={})
        project.scenes.append(
            factory.Scene(0, "CIN", "Intro", 2, "music.mp3", video_path="")
        )
        with self.assertRaisesRegex(RuntimeError, "has no rendered video"):
            factory.validate_project(project)

    def test_get_duration_reports_ffprobe_failure(self):
        with patch("ai_video_factory.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "ffprobe error"
            with self.assertRaisesRegex(RuntimeError, "FFprobe failed"):
                factory.get_duration("missing.mp4")


if __name__ == "__main__":
    unittest.main()
