# PDF to Educational Video

Turn a PDF into an MP4 educational walkthrough with an AI-written teaching
script, spoken narration, page visuals, captions, and a downloadable ZIP.

[![Open in Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jromjenine76-alt/pdf-to-video-converter/blob/main/PDF_to_Educational_Video.ipynb)

## Simplest setup: Android phone + Google Colab

You do **not** need Termux, Python, or FFmpeg on your phone.

1. Create an API key in your OpenAI Platform project. API billing is separate
   from a ChatGPT subscription.
2. Tap the **Open in Google Colab** button above.
3. In Colab, tap the key icon named **Secrets** in the left menu.
4. Add a secret named exactly `OPENAI_API_KEY`, paste the key as its value, and
   switch **Notebook access** on. Never paste the key into a notebook cell,
   GitHub file, screenshot, or chat.
5. Run the first setup cell and wait for its green check mark.
6. Run the second launch cell. It displays a private six-digit PIN and a public
   Gradio link protected by that PIN.
7. Open the link, sign in with username `video` and the displayed PIN, upload
   your PDF, and tap **Create my educational video**.
8. Keep the Colab and converter tabs open. When it finishes, download the ZIP.

For a quick, lower-cost first test, use pages `1-5`, **Detailed** narration,
**Landscape (16:9)**, **720p**, and **Standard PDF analysis**.

## What you receive

- An MP4 in landscape, vertical, or both formats
- An editable JSON narration script
- An SRT captions file
- A ZIP containing the complete package

The app supports up to 50 selected pages per run. It clearly discloses that the
voice is AI-generated. Review the script before publishing high-stakes or
disputed material.

## Privacy and security

- The API key is read from Colab Secrets and is never written into an output.
- Small temporary PDF batches are uploaded to the OpenAI API for analysis and
  deleted from the API after each batch on a best-effort basis.
- Intermediate PDF images and narration WAV files are deleted after packaging.
- The Colab runtime and converter link are temporary. Stop the runtime when
  finished, and do not share the link or PIN.
- `.env` files, generated audio, and generated videos are ignored by Git.

## Troubleshooting

| What you see | What to do |
|---|---|
| `OPENAI_API_KEY was not found` | Reopen Colab **Secrets**, check the exact name, and enable notebook access. |
| `API key was rejected` | Create a new active project key, replace the Colab secret, and revoke the old key if it may have been exposed. |
| Usage limit or API credit message | Check **Billing** at platform.openai.com, then retry with pages `1-3`. |
| PDF cannot be processed | Use an unlocked PDF, select fewer pages, or save/print the document as a new PDF first. |
| Colab disconnected | Reconnect, rerun both cells, and reopen the newly generated converter link. |
| Link asks for a login | Use username `video` and the six-digit PIN shown by the launch cell. |
| Conversion seems slow | Keep both tabs open; use 720p, one format, and 1-5 pages for the first run. |
| Phone runs out of space | Download only the ZIP, confirm it opens, then remove duplicate individual downloads. |

## Optional computer setup

Python 3.11+ and FFmpeg are required.

```bash
git clone https://github.com/jromjenine76-alt/pdf-to-video-converter.git
cd pdf-to-video-converter
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export OPENAI_API_KEY="your-key-here"
python app.py
```

Do not put a real API key in a committed file.
