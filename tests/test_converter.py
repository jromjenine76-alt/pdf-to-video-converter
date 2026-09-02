from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pymupdf as fitz
import pytest
import pdf_video_converter as converter_module

from pdf_video_converter import (
    ConversionSettings,
    SceneScript,
    _validate_script_pages,
    caption_chunks,
    create_video_segment,
    convert_pdf,
    parse_page_selection,
    render_scene_frame,
    safe_stem,
    split_for_tts,
    write_silence_wav,
    write_srt,
)


def test_parse_page_selection() -> None:
    assert parse_page_selection("1-3,2,5", 8) == [1, 2, 3, 5]
    assert parse_page_selection("all", 3) == [1, 2, 3]
    assert parse_page_selection("1-10", 4) == [1, 2, 3, 4]


@pytest.mark.parametrize("selection", ["0", "9", "3-2", "words", "9-10"])
def test_parse_page_selection_rejects_invalid_values(selection: str) -> None:
    with pytest.raises(ValueError):
        parse_page_selection(selection, 8)


def test_page_limit() -> None:
    with pytest.raises(ValueError, match="no more than 50"):
        parse_page_selection("all", 51)


def test_safe_filename_and_tts_split() -> None:
    assert safe_stem("  My lesson: chapter / 1  ") == "My_lesson_chapter_1"
    text = "One short sentence. " * 20
    parts = split_for_tts(text, max_chars=80)
    assert len(parts) > 1
    assert all(len(part) <= 80 for part in parts)
    assert " ".join(parts).replace("  ", " ") == text.strip()


def test_script_validation_orders_pages() -> None:
    scenes = [
        SceneScript(page_number=3, heading="Third", narration="C", takeaway="C"),
        SceneScript(page_number=2, heading="Second", narration="B", takeaway="B"),
    ]
    ordered = _validate_script_pages(scenes, [2, 3])
    assert [scene.page_number for scene in ordered] == [2, 3]


def test_captions_and_srt(tmp_path: Path) -> None:
    narration = "This is a useful educational sentence with enough words to caption clearly."
    scene = SceneScript(
        page_number=1,
        heading="Lesson",
        narration=narration,
        takeaway="Learn clearly.",
    )
    assert caption_chunks(narration)
    path = tmp_path / "captions.srt"
    write_srt([scene], [5.35], path)
    content = path.read_text(encoding="utf-8")
    assert "00:00:02,850" in content
    assert narration in content.replace("\n", " ")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is unavailable")
def test_local_video_segment_smoke(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    with fitz.open() as document:
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 100), "A small educational PDF", fontsize=24)
        page.insert_text((72, 150), "This page explains a local smoke test.", fontsize=14)
        document.save(pdf_path)

    scene = SceneScript(
        page_number=1,
        heading="Local Smoke Test",
        narration="This narration is replaced by silence during the local test.",
        takeaway="The rendering pipeline works without an API key.",
    )
    image_path = tmp_path / "frame.png"
    audio_path = tmp_path / "audio.wav"
    video_path = tmp_path / "segment.mp4"
    with fitz.open(pdf_path) as document:
        render_scene_frame(document[0], scene, image_path, size=(640, 360))
    write_silence_wav(audio_path, 0.25)
    duration = create_video_segment(
        image_path,
        audio_path,
        video_path,
        size=(640, 360),
        crf="28",
    )

    assert duration == pytest.approx(0.60, abs=0.02)
    assert video_path.stat().st_size > 1_000
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert {stream["codec_type"] for stream in streams} == {"video", "audio"}


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is unavailable")
def test_temporary_files_are_cleaned_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_path = tmp_path / "source.pdf"
    with fitz.open() as document:
        document.new_page()
        document.save(pdf_path)

    monkeypatch.setattr(converter_module, "OpenAI", lambda api_key: object())

    def fail_script(*args: object, **kwargs: object) -> object:
        raise RuntimeError("deliberate test failure")

    monkeypatch.setattr(converter_module, "generate_educational_script", fail_script)
    output_root = tmp_path / "output"
    with pytest.raises(RuntimeError, match="deliberate"):
        convert_pdf(
            pdf_path,
            ConversionSettings(title="Test", page_selection="1"),
            api_key="not-a-real-key",
            output_root=output_root,
        )

    job_dirs = list(output_root.iterdir())
    assert len(job_dirs) == 1
    assert not list(job_dirs[0].glob("work_*"))
