"""Business logic: fetch metadata, transcripts, and produce the output file for VanScript."""

from collections.abc import Callable
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import YouTubeTranscriptApiException

from models import (
    AppConfig,
    DownloadStatus,
    MetadataFetchError,
    TranscriptFetchError,
    TranscriptSnippet,
    VideoMetadata,
    VideoResult,
    VideoTranscript,
)
from utils import (
    build_output_filename,
    ensure_unique_path,
    extract_video_id,
    parse_url_list,
)

# Type alias for the progress callback: (message: str, progress_fraction: float)
ProgressCallback = Callable[[str, float], None]


def fetch_metadata(video_id: str) -> VideoMetadata:
    """Fetch video metadata using yt-dlp (no download)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError, OSError) as exc:
        raise MetadataFetchError(f"Failed to fetch metadata for {video_id}: {exc}") from exc

    raw_date = info.get("upload_date", "") or ""  # YYYYMMDD
    if len(raw_date) == 8:
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    else:
        formatted_date = raw_date

    return VideoMetadata(
        video_id=video_id,
        title=info.get("title", "Unknown Title"),
        upload_date=formatted_date,
        channel=info.get("channel", info.get("uploader", "Unknown Channel")),
        duration=int(info.get("duration", 0) or 0),
        url=url,
    )


def fetch_transcript(video_id: str, languages: list[str]) -> VideoTranscript:
    """Fetch transcript using youtube-transcript-api v1.x."""
    api = YouTubeTranscriptApi()

    try:
        fetched = api.fetch(video_id, languages=languages)
    except YouTubeTranscriptApiException:
        # Languages not found directly — fall back to first available
        try:
            transcript_list = api.list(video_id)
            first = next(iter(transcript_list), None)
            if first is None:
                raise TranscriptFetchError(f"No transcript found for {video_id}")
            fetched = first.fetch()
        except TranscriptFetchError:
            raise
        except YouTubeTranscriptApiException as exc:
            raise TranscriptFetchError(f"No transcripts available for {video_id}: {exc}") from exc

    lang_label = fetched.language
    if fetched.is_generated:
        lang_label += f" ({fetched.language_code}) [auto-generated]"
    else:
        lang_label += f" ({fetched.language_code})"

    snippets = [
        TranscriptSnippet(text=s.text, start=s.start, duration=s.duration)
        for s in fetched.snippets
    ]

    return VideoTranscript(video_id=video_id, language=lang_label, snippets=snippets)


def process_single_video(video_id: str, languages: list[str]) -> VideoResult:
    """Fetch metadata + transcript for one video. Never raises — captures errors in VideoResult."""
    result = VideoResult(video_id=video_id, status=DownloadStatus.FETCHING_METADATA)

    try:
        result.metadata = fetch_metadata(video_id)
    except MetadataFetchError as exc:
        result.status = DownloadStatus.FAILED
        result.error_message = str(exc)
        return result

    result.status = DownloadStatus.FETCHING_TRANSCRIPT
    try:
        result.transcript = fetch_transcript(video_id, languages)
    except TranscriptFetchError as exc:
        result.status = DownloadStatus.FAILED
        result.error_message = str(exc)
        return result

    result.status = DownloadStatus.SUCCESS
    return result


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to [HH:MM:SS] format."""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def format_video_section(result: VideoResult, config: AppConfig, index: int, total: int) -> str:
    """Format a single video's section for the output file."""
    sep = config.separator
    lines: list[str] = []

    lines.append("")
    lines.append(sep)
    lines.append(f"  VIDEO {index} of {total}")
    lines.append(sep)

    if result.metadata:
        m = result.metadata
        lines.append(f"  Title:    {m.title}")
        lines.append(f"  Channel:  {m.channel}")
        lines.append(f"  Date:     {m.upload_date}")
        lines.append(f"  URL:      {m.url}")
    else:
        lines.append(f"  Video ID: {result.video_id}")

    if result.transcript:
        t = result.transcript
        lines.append(f"  Language: {t.language}")
        lines.append(f"  Lines:    {len(t.snippets)}")
    elif result.status == DownloadStatus.FAILED:
        lines.append("  Status:   FAILED")

    lines.append(sep)
    lines.append("")

    if result.transcript and result.transcript.snippets:
        for snippet in result.transcript.snippets:
            if config.include_timestamps:
                lines.append(f"{_format_timestamp(snippet.start)} {snippet.text}")
            else:
                lines.append(snippet.text)
    elif result.error_message:
        lines.append(f"[Transcript unavailable: {result.error_message}]")
    else:
        lines.append("[Transcript unavailable]")

    lines.append("")
    return "\n".join(lines)


def process_all_videos(
    raw_text: str,
    config: AppConfig,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """Main orchestrator: parse URLs, fetch all, write output file. Returns the output path."""
    def _noop(msg: str, frac: float) -> None:
        pass

    if on_progress is None:
        on_progress = _noop

    # Parse URLs
    on_progress("Parsing URLs...", 0.0)
    video_ids = parse_url_list(raw_text)

    if not video_ids:
        # Try treating the entire text as individual lines that might be invalid
        # Re-parse to give better error reporting
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        invalid = []
        for line in lines:
            try:
                extract_video_id(line)
            except Exception:
                invalid.append(line)
        if invalid:
            raise ValueError(f"No valid YouTube URLs found. Invalid entries:\n" + "\n".join(invalid[:5]))
        raise ValueError("No YouTube URLs provided.")

    total = len(video_ids)
    on_progress(f"Found {total} video(s). Starting...", 0.05)

    # Process each video
    results: list[VideoResult] = []
    for i, vid in enumerate(video_ids, 1):
        on_progress(f"[{i}/{total}] Fetching metadata for {vid}...", (i - 1) / total * 0.9 + 0.05)
        result = process_single_video(vid, config.languages)
        results.append(result)

        if result.status == DownloadStatus.SUCCESS:
            title = result.metadata.title if result.metadata else vid
            on_progress(f"[{i}/{total}] Done: {title}", i / total * 0.9 + 0.05)
        else:
            on_progress(f"[{i}/{total}] Failed: {result.error_message[:80]}", i / total * 0.9 + 0.05)

    # Build output
    on_progress("Building output file...", 0.95)

    success_count = sum(1 for r in results if r.status == DownloadStatus.SUCCESS)
    sep = config.separator

    header_lines = [
        sep,
        "  VANSCRIPT — YouTube Transcripts",
        f"  {success_count} of {total} video(s) transcribed successfully",
        sep,
    ]
    header = "\n".join(header_lines)

    body_parts = []
    for i, result in enumerate(results, 1):
        body_parts.append(format_video_section(result, config, i, total))

    full_text = header + "\n" + "\n".join(body_parts)

    # Determine filename
    titles = [r.metadata.title for r in results if r.metadata]
    dates = [r.metadata.upload_date for r in results if r.metadata and r.metadata.upload_date]
    filename = build_output_filename(titles, dates)

    output_dir = Path(config.output_folder) if config.output_folder else Path.home() / "Downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = ensure_unique_path(output_dir / filename)

    output_path.write_text(full_text, encoding="utf-8")
    on_progress(f"Saved to: {output_path}", 1.0)

    return output_path
