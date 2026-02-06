# VanScript

YouTube transcript downloader with a modern desktop GUI. Paste one or more YouTube URLs, pick your language, and get a clean `.txt` file with all transcripts merged — ready for studying, note-taking, or feeding into an LLM.

Built by **VanDev**.

## Features

- Paste multiple YouTube URLs and download all transcripts at once
- Auto-detects available languages (Spanish, English, Portuguese, French, German)
- Optional timestamps `[HH:MM:SS]` per line
- Output file named automatically from video titles and dates
- One failed video never stops the rest
- Dark UI with a dev-tool aesthetic

## Screenshot

> Run the app and see for yourself :)

## Requirements

- Python 3.10+
- Internet connection

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

1. Paste YouTube URLs (one per line) into the text area
2. Choose the preferred language
3. Optionally enable timestamps
4. Choose the output folder (defaults to your Downloads)
5. Click **Download Transcripts**

The output `.txt` file will contain all transcripts with headers showing title, channel, date, and URL for each video.

## Build as .exe (Windows)

```bash
pyinstaller build.spec --noconfirm
```

The executable will be in `dist/VanScript/`.

## Project Structure

```
├── main.py           # Entry point
├── app.py            # CustomTkinter GUI
├── core.py           # Download + merge logic
├── models.py         # Dataclasses and exceptions
├── utils.py          # URL parsing, filename utils
├── requirements.txt  # Dependencies
├── build.spec        # PyInstaller config
└── LICENSE           # CC BY-NC 4.0
```

## Tech Stack

| Component     | Library                  |
|---------------|--------------------------|
| GUI           | CustomTkinter            |
| Transcripts   | youtube-transcript-api   |
| Video metadata| yt-dlp                   |
| Packaging     | PyInstaller              |

## License

This project is licensed under [CC BY-NC 4.0](LICENSE) — free for educational and personal use. Not for commercial use.
