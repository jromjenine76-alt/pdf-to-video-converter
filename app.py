"""Phone-friendly Gradio interface for the PDF video converter."""

from __future__ import annotations

import re
from pathlib import Path

import gradio as gr
from openai import APIConnectionError, AuthenticationError, BadRequestError, RateLimitError

from pdf_video_converter import (
    DEPTH_WORD_RANGES,
    QUALITY_SPECS,
    VOICE_OPTIONS,
    ConversionSettings,
    convert_pdf,
    load_api_key,
)


DEFAULT_FOCUS = (
    "Create a clear educational video walkthrough. Explain the PDF in plain "
    "language, preserve important details, and connect each page naturally."
)
DEFAULT_VOICE_STYLE = (
    "Speak as a warm, calm educational guide. Use a natural pace, clear "
    "pronunciation, gentle emphasis, and brief pauses between ideas."
)

APP_THEME = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate",
)
APP_CSS = """
.gradio-container { max-width: 980px !important; margin: 0 auto !important; }
.hero { text-align: center; padding: 0.4rem 0 0.8rem; }
.hero h1 { margin-bottom: 0.25rem; }
.privacy-note { border-left: 4px solid #3b82f6; padding-left: 0.8rem; }
@media (max-width: 640px) {
  .gradio-container { padding-left: 10px !important; padding-right: 10px !important; }
  button.primary { min-height: 52px !important; font-size: 1.05rem !important; }
}
"""


def _clean_error(message: str) -> str:
    """Keep UI errors useful without ever echoing a credential-like value."""

    return re.sub(r"sk-[A-Za-z0-9_-]+", "[hidden key]", message).strip()


def _friendly_error(error: Exception) -> str:
    if isinstance(error, AuthenticationError):
        return (
            "The API key was rejected. In Colab Secrets, replace "
            "OPENAI_API_KEY with an active key and enable notebook access."
        )
    if isinstance(error, RateLimitError):
        return (
            "OpenAI paused the request because of a usage limit or missing API "
            "credit. Check Billing on platform.openai.com, then try fewer pages."
        )
    if isinstance(error, APIConnectionError):
        return "The service could not be reached. Check your connection and try again."
    if isinstance(error, BadRequestError):
        return (
            "The PDF could not be processed by the narration service. Try pages "
            "1-3 first, or use a smaller/unlocked PDF. Details: "
            + _clean_error(str(error))[-500:]
        )
    return _clean_error(str(error)) or "The conversion stopped unexpectedly."


def _convert_from_form(
    pdf_file: str | None,
    title: str,
    page_selection: str,
    depth: str,
    focus: str,
    voice: str,
    voice_style: str,
    output_format: str,
    quality: str,
    pdf_detail_label: str,
    progress: gr.Progress = gr.Progress(track_tqdm=False),
) -> tuple[str, str | None, list[str]]:
    if not pdf_file:
        return "### Add a PDF first", None, []

    settings = ConversionSettings(
        title=title,
        page_selection=page_selection,
        depth=depth,
        focus=focus,
        voice=voice,
        voice_style=voice_style,
        output_format=output_format,
        quality=quality,
        pdf_detail="high" if pdf_detail_label.startswith("High") else "low",
    )

    def report(value: float, description: str) -> None:
        progress(value, desc=description)

    try:
        api_key = load_api_key()
        artifacts, summary = convert_pdf(
            pdf_file,
            settings,
            api_key=api_key,
            output_root=Path.cwd() / "output",
            progress=report,
        )
        paths = [str(path.resolve()) for path in artifacts]
        first_video = next((path for path in paths if path.endswith(".mp4")), None)
        return (
            "### Video ready\n"
            f"{summary} Download the ZIP to keep the video, captions, and script together.",
            first_video,
            paths,
        )
    except Exception as error:
        return f"### Conversion stopped\n{_friendly_error(error)}", None, []


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="PDF to Educational Video") as demo:
        gr.HTML(
            """
            <div class="hero">
              <h1>PDF to Educational Video</h1>
              <p>Upload a PDF, generate a teaching script, add narration, and download an MP4.</p>
            </div>
            """
        )
        gr.Markdown(
            "**Safe first test:** choose a short PDF or pages `1-5`, use "
            "**720p**, and keep this browser tab open while it works."
        )

        pdf_file = gr.File(
            label="1. Upload your PDF",
            file_types=[".pdf"],
            type="filepath",
        )

        with gr.Accordion("2. What should the video teach?", open=True):
            title = gr.Textbox(
                label="Video title (optional)",
                placeholder="The app can create a title from your PDF",
            )
            page_selection = gr.Textbox(
                label="PDF pages",
                value="1-5",
                info="Examples: 1-5 or 1-3,7,10. Maximum 50 pages per run.",
            )
            depth = gr.Radio(
                choices=list(DEPTH_WORD_RANGES),
                value="Detailed",
                label="Explanation depth",
            )
            focus = gr.Textbox(
                label="Teaching instructions",
                value=DEFAULT_FOCUS,
                lines=3,
            )

        with gr.Accordion("3. Narrator and video style", open=False):
            voice = gr.Dropdown(
                choices=list(VOICE_OPTIONS),
                value="marin",
                label="Narrator voice",
                info="Marin is a clear, natural default.",
            )
            voice_style = gr.Textbox(
                label="How the narrator should sound",
                value=DEFAULT_VOICE_STYLE,
                lines=3,
            )
            output_format = gr.Radio(
                choices=[
                    "Landscape (16:9)",
                    "Vertical (9:16)",
                    "Both landscape and vertical",
                ],
                value="Landscape (16:9)",
                label="Video shape",
            )
            quality = gr.Radio(
                choices=list(QUALITY_SPECS),
                value="720p (faster)",
                label="Video quality",
            )
            pdf_detail = gr.Radio(
                choices=["Standard PDF analysis", "High-detail PDF analysis"],
                value="Standard PDF analysis",
                label="PDF analysis quality",
                info="High detail can help tiny text but may use more API tokens.",
            )

        convert_button = gr.Button(
            "Create my educational video",
            variant="primary",
            size="lg",
        )
        status = gr.Markdown("Ready for your PDF.")
        preview = gr.Video(label="Video preview", interactive=False)
        downloads = gr.File(
            label="Download video package and files",
            file_count="multiple",
            interactive=False,
        )
        gr.Markdown(
            "<span class='privacy-note'>The key is read from Colab Secrets and "
            "is never placed in your PDF, video, downloads, or GitHub. Narration "
            "is AI-generated and the video states this.</span>"
        )

        convert_button.click(
            fn=_convert_from_form,
            inputs=[
                pdf_file,
                title,
                page_selection,
                depth,
                focus,
                voice,
                voice_style,
                output_format,
                quality,
                pdf_detail,
            ],
            outputs=[status, preview, downloads],
        )

    return demo


if __name__ == "__main__":
    build_demo().queue(default_concurrency_limit=1).launch(
        theme=APP_THEME,
        css=APP_CSS,
    )
