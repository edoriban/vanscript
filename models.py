"""Data models and custom exceptions for VanScript."""

from dataclasses import dataclass, field
from enum import Enum


# --- Custom Exceptions ---

class TranscriptAppError(Exception):
    """Base exception for the app."""


class InvalidURLError(TranscriptAppError):
    """Raised when a URL/ID cannot be parsed."""


class MetadataFetchError(TranscriptAppError):
    """Raised when yt-dlp fails to fetch video metadata."""


class TranscriptFetchError(TranscriptAppError):
    """Raised when youtube-transcript-api fails."""


class WhisperFetchError(TranscriptAppError):
    """Raised when Whisper transcription fails."""


# --- Enums ---

class DownloadStatus(Enum):
    PENDING = "pending"
    FETCHING_METADATA = "fetching_metadata"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    SUCCESS = "success"
    FAILED = "failed"


class WhisperModelSize(Enum):
    TINY = "tiny"       # ~39 MB
    BASE = "base"       # ~74 MB
    SMALL = "small"     # ~244 MB


# --- Dataclasses ---

@dataclass
class VideoMetadata:
    video_id: str
    title: str
    upload_date: str  # YYYY-MM-DD
    channel: str
    duration: int  # seconds
    url: str


@dataclass
class TranscriptSnippet:
    text: str
    start: float
    duration: float


@dataclass
class VideoTranscript:
    video_id: str
    language: str
    snippets: list[TranscriptSnippet] = field(default_factory=list)


@dataclass
class VideoResult:
    video_id: str
    metadata: VideoMetadata | None = None
    transcript: VideoTranscript | None = None
    status: DownloadStatus = DownloadStatus.PENDING
    error_message: str = ""


@dataclass
class LocalFileResult:
    file_path: str
    file_name: str
    transcript: VideoTranscript | None = None
    status: DownloadStatus = DownloadStatus.PENDING
    error_message: str = ""


@dataclass
class AppConfig:
    output_folder: str = ""
    languages: list[str] = field(default_factory=lambda: ["es", "en"])
    include_timestamps: bool = False
    separator: str = "=" * 72
