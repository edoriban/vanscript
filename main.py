"""Entry point for the YouTube Transcript Downloader."""

from app import TranscriptDownloaderApp


def main() -> None:
    app = TranscriptDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
