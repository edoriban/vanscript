# VanScript

YouTube transcript downloader and local file transcriber with a modern desktop GUI. Paste YouTube URLs to download transcripts, or select local video/audio files to transcribe with Whisper AI — all in one app.

Built by **VanDev**.

## Features

### YouTube Transcripts
- Paste multiple YouTube URLs and download all transcripts at once
- Auto-detects available languages (Spanish, English, Portuguese, French, German)
- One failed video never stops the rest

### Local File Transcription (Whisper)
- Transcribe local video/audio files (.mp4, .mkv, .mp3, .wav, .m4a, .webm, .ogg, .flac)
- Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2)
- Whisper model (base) bundled — no download needed on first use
- Supports 9 languages + auto-detect

### Shared
- Optional timestamps `[HH:MM:SS]` per line
- Output file named automatically from video titles / file names
- Auto-opens the output file when done
- Dark UI with a dev-tool aesthetic
- Tabbed interface: **YouTube URLs** | **Local Files**

## Screenshot

> Run the app and see for yourself :)

## Requirements

- Python 3.10+
- Internet connection (for YouTube transcripts)

## Installation

```bash
# Clone the repo
git clone https://github.com/edoriban/vanscript.git
cd vanscript

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### YouTube URLs tab
1. Paste YouTube URLs (one per line) into the text area
2. Choose the preferred language
3. Optionally enable timestamps
4. Click **Download Transcripts**

### Local Files tab
1. Click **Select Files** to choose video/audio files
2. Pick the Whisper model size (tiny / base / small)
3. Choose the language (or auto-detect)
4. Click **Transcribe**

The output `.txt` file will open automatically when done.

## Build as .exe (Windows)

```bash
pyinstaller build.spec --noconfirm
```

The executable will be in `dist/VanScript/`. The Whisper base model is bundled automatically.

## Project Structure

```
├── main.py              # Entry point
├── app.py               # CustomTkinter GUI (tabbed)
├── core.py              # YouTube + Whisper transcription logic
├── models.py            # Dataclasses and exceptions
├── utils.py             # URL parsing, filename utils
├── requirements.txt     # Dependencies
├── build.spec           # PyInstaller config
├── whisper_models/      # Bundled Whisper model (base)
└── LICENSE              # CC BY-NC 4.0
```

## Tech Stack

| Component          | Library                |
|--------------------|------------------------|
| GUI                | CustomTkinter          |
| YouTube Transcripts| youtube-transcript-api |
| Video metadata     | yt-dlp                 |
| Local transcription| faster-whisper         |
| Packaging          | PyInstaller            |

## License

This project is licensed under [CC BY-NC 4.0](LICENSE) — free for educational and personal use. Not for commercial use.
