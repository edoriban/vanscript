# VanScript

YouTube transcript downloader with a dark desktop GUI. Paste YouTube URLs, get a
formatted transcript file.

Built by **VanDev**.

> **v2.0 — ported from Python to Rust.** The YouTube side is now a single 7 MB
> native binary with no runtime dependencies, down from 78 MB. The Python app
> lives on for Whisper transcription of local files. See
> [Which version do I want?](#which-version-do-i-want) below.

## Features

- Paste multiple YouTube URLs and download all transcripts at once
- Language preference with fallback (Spanish, English, Portuguese, French, German)
- One failed video never stops the rest
- Optional timestamps `[HH:MM:SS]` per line
- Output file named automatically from video titles and dates
- Auto-opens the output file when done
- Dark UI with a dev-tool aesthetic
- Also runs headless as a CLI

### Local file transcription (Python version only)

- Transcribe local video/audio files (.mp4, .mkv, .mp3, .wav, .m4a, .webm, .ogg, .flac)
- Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2)
- Whisper model (base) bundled — no download needed on first use
- Supports 9 languages + auto-detect

## Which version do I want?

|                        | Rust (`vanscript-rs/`) | Python (repo root) |
|------------------------|------------------------|--------------------|
| YouTube transcripts    | yes                    | yes                |
| Local files (Whisper)  | no                     | yes                |
| Binary size            | ~7 MB                  | ~78 MB (lite) / ~450 MB (with Whisper) |
| Runtime dependencies   | none                   | Python + yt-dlp + youtube-transcript-api |
| Startup                | instant                | interpreter + imports |

Both produce byte-identical output files. Take the Rust build unless you need
Whisper.

## Install

Download a build from [Releases](https://github.com/edoriban/vanscript/releases),
extract, and run — nothing to install.

- Linux: `VanScript-v2.0-linux-x86_64.tar.gz` → `./VanScript`
- Windows: `VanScript-v2.0-win64.zip` → `VanScript.exe`

## Usage (Rust)

Launch with no arguments for the GUI:

1. Paste YouTube URLs (one per line) into the text area
2. Choose the preferred language
3. Optionally enable timestamps
4. Click **Download Transcripts**

The output `.txt` opens automatically when done.

Pass arguments and it runs as a CLI instead:

```bash
vanscript https://youtu.be/dQw4w9WgXcQ            # one video
vanscript --stdin -t -l es,en < urls.txt          # a list, with timestamps
vanscript --help
```

| Option | Meaning |
|--------|---------|
| `-l`, `--lang <CODES>` | Comma-separated language preference (default `es,en`) |
| `-o`, `--out <DIR>` | Output directory (default `~/Downloads`) |
| `-t`, `--timestamps` | Prefix every line with `[HH:MM:SS]` |
| `--stdin` | Read URLs from standard input, one per line |

## Usage (Python, for Whisper)

```bash
pip install -r requirements.txt
python main.py
```

The **Local Files** tab appears only when `faster-whisper` is installed, so a
lite install gives you the YouTube tab alone.

1. Click **Select Files** to choose video/audio files
2. Pick the Whisper model size (tiny / base / small)
3. Choose the language (or auto-detect)
4. Click **Transcribe**

## Building

### Rust

```bash
make rs-build     # release binary in vanscript-rs/target/release/
make rs-test      # clippy -D warnings, then the test suite
```

Cross-compiling for Windows needs [cargo-xwin](https://github.com/rust-cross/cargo-xwin):

```bash
cargo install cargo-xwin
rustup target add x86_64-pc-windows-msvc
cd vanscript-rs && cargo xwin build --release --target x86_64-pc-windows-msvc
```

### Python

```bash
pyinstaller build.spec --noconfirm    # full build, Whisper model bundled
make build-lite                       # YouTube only, no Whisper
```

## How it works

The Rust version talks to YouTube's InnerTube API directly, which is what
replaced both Python dependencies:

1. `GET` the watch page once — scrape the `INNERTUBE_API_KEY` (it rotates, so it
   cannot be hardcoded) and the upload date.
2. `POST youtubei/v1/player` with that key and an ANDROID client context. The
   response carries the video metadata *and* caption track URLs that work without
   a proof-of-origin token, which the ones on the watch page do not.
3. `GET` the chosen caption track as `json3`.

## Project Structure

```
├── vanscript-rs/            # Rust port (v2.0) — YouTube transcripts
│   ├── src/youtube.rs       #   InnerTube API client
│   ├── src/output.rs        #   URL parsing, formatting, filenames
│   ├── src/gui.rs           #   egui interface
│   └── src/main.rs          #   GUI launcher + CLI
├── main.py                  # Python entry point
├── app.py                   # CustomTkinter app shell (tabbed)
├── theme.py                 # Colours and language presets
├── ui/                      # Reusable widgets and layout sections
├── core.py                  # YouTube + Whisper transcription logic
├── models.py                # Dataclasses and exceptions
├── utils.py                 # URL parsing, filename utils
├── build.spec               # PyInstaller config (LITE=1 skips Whisper)
├── assets/                  # App icons (ico / icns / png)
├── whisper_models/          # Bundled Whisper model (base)
└── LICENSE                  # CC BY-NC 4.0
```

## Tech Stack

| Component           | Rust            | Python                 |
|---------------------|-----------------|------------------------|
| GUI                 | egui / eframe   | CustomTkinter          |
| YouTube transcripts | InnerTube + reqwest | youtube-transcript-api |
| Video metadata      | InnerTube + reqwest | yt-dlp             |
| Local transcription | —               | faster-whisper         |
| Packaging           | cargo           | PyInstaller            |

## License

This project is licensed under [CC BY-NC 4.0](LICENSE) — free for educational and personal use. Not for commercial use.
